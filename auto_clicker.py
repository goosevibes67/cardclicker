"""Desktop NoPixel giveaway helper. Controls a dedicated Microsoft Edge profile; no extension needed."""
import json
import os
import queue
import re
import subprocess
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox
from urllib.request import urlopen

APP = "CardClicker"
NP_EXT = "nstuq90nghenyqwqme61jgvmtp253a"
NP_HOST = "nopixel.streamingtoolsmith.com"
JOIN_PATH = "/channel/giveaway/join"
JOIN_GAP = 15
WIN = re.compile(r"\b(you|you['’]ve|you have)\s+(won|win|got|received)\b(?!['’]?t)|congrat|you['’]re a winner|winner!", re.I)
LOSS = re.compile(r"didn['’]?t get a pack|better luck|unlucky|no luck|not a winner|not this time", re.I)
RESERVED = {"directory","videos","search","downloads","p","settings","subscriptions","inventory","drops","wallet","friends","messages","turbo","jobs","store","following","team","event","collections","clip","bits","broadcast","login","signup","privacy","legal","user","about","moderator","embed","dashboard","u","prime"}

def app_dir():
    root = Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP
    root.mkdir(parents=True, exist_ok=True)
    return root

def channel_of(url):
    m = re.match(r"https?://(?:www\.)?twitch\.tv/([^/?#]+)", url or "", re.I)
    name = m.group(1).lower() if m else ""
    return name if re.fullmatch(r"[a-z0-9_]{3,25}", name) and name not in RESERVED else None

def edge_path():
    candidates = [
        Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Edge/Application/msedge.exe",
    ]
    return next((p for p in candidates if p.is_file()), None)

class BrowserWorker(threading.Thread):
    def __init__(self, events):
        super().__init__(daemon=True)
        self.events = events
        self.commands = queue.Queue()
        self.halt = threading.Event()
        self.wake_abort = threading.Event()
        self.play = self.browser = self.context = None
        self.edge = None
        self.enabled = False
        self.pages = {}
        self.stats_path = app_dir() / "stats.json"
        try:
            self.stats = json.loads(self.stats_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.stats = {}
        self.logs = []
        self.wake_minutes = 3
        self.wake_enabled = False
        self.next_wake = 0
        self.last_wake = 0
        self.waking = False

    def emit(self, kind, **data):
        self.events.put({"type": kind, **data})

    def log(self, channel, message, level="info"):
        row = {"time": time.time(), "channel": channel or "", "message": message, "level": level}
        self.logs.insert(0, row)
        self.logs = self.logs[:150]
        self.emit("log", row=row)

    def save_stats(self):
        p = self.stats_path.with_suffix(".tmp")
        p.write_text(json.dumps(self.stats, indent=2), encoding="utf-8")
        p.replace(self.stats_path)

    def connect_edge(self):
        if self.context:
            return
        exe = edge_path()
        if not exe:
            raise RuntimeError("Microsoft Edge was not found. Install Edge and try again.")
        profile = app_dir() / "EdgeProfile"
        profile.mkdir(exist_ok=True)
        active = profile / "DevToolsActivePort"
        active.unlink(missing_ok=True)
        args = [str(exe), "--remote-debugging-port=0", "--remote-debugging-address=127.0.0.1",
                "--remote-allow-origins=*", f"--user-data-dir={profile}", "--no-first-run",
                "--no-default-browser-check", "https://www.twitch.tv/"]
        self.edge = subprocess.Popen(args)
        self.emit("status", text="Opening dedicated Edge profile…")
        deadline = time.time() + 30
        while time.time() < deadline and not self.halt.is_set():
            if active.exists():
                try:
                    port = active.read_text().splitlines()[0].strip()
                    with urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1):
                        break
                except Exception:
                    pass
            time.sleep(.25)
        else:
            raise RuntimeError("Edge did not start its local control endpoint.")
        from playwright.sync_api import sync_playwright
        self.play = sync_playwright().start()
        self.browser = self.play.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        self.context = self.browser.contexts[0]
        self.emit("status", text="Edge connected. Sign in to Twitch, open channels, then Start monitoring.")
        self.log("", "Connected to a dedicated Edge profile. Twitch login stays in that profile.")

    def response(self, response, state):
        try:
            url = response.url
            if NP_HOST not in url:
                return
            path = re.sub(r"https?://[^/]+", "", url).split("?", 1)[0]
            if path != JOIN_PATH:
                return
            ch = state["channel"]
            status = response.status
            if 200 <= status < 300:
                state["last_server_join"] = time.time()
                state["pending_until"] = 0
                state["phase"] = "Joined"
                if time.time() - state["overlay_join_at"] > 15:
                    self.bump(ch, "joined")
                self.log(ch, f"Server accepted giveaway join (HTTP {status}).", "ok")
            elif status == 401:
                state["got_401"] = True
                state["phase"] = "Session expired"
                self.log(ch, "Giveaway server returned HTTP 401.", "warn")
            else:
                state["pending_until"] = 0
                state["phase"] = f"Join rejected ({status})"
                self.log(ch, f"Join rejected (HTTP {status}).", "bad")
        except Exception:
            pass

    def open_channels(self, names):
        self.connect_edge()
        for name in names:
            self.context.new_page().goto(f"https://www.twitch.tv/{name}", wait_until="domcontentloaded", timeout=30000)
            self.log(name, "Opened Twitch channel in the app's Edge profile.")

    def refresh_pages(self):
        found = {}
        for page in list(self.context.pages):
            ch = channel_of(page.url)
            if not ch:
                continue
            key = id(page)
            if key not in self.pages:
                self.pages[key] = {"page": page, "channel": ch, "last_click": 0,
                                   "phase": "Waiting", "note": "", "joined_text": False,
                                   "outcome": "", "reloads": [], "last_reload": 0,
                                   "captures": set(), "counted_text": False,
                                   "last_server_join": 0, "overlay_join_at": 0,
                                   "dismissed": False, "pending_until": 0,
                                   "attempts": 0, "active_banner": False}
                page.on("response", lambda response, s=self.pages[key]: self.response(response, s))
            state = self.pages[key]
            state["channel"] = ch
            found[key] = state
        self.pages = found
        return list(found.values())

    def overlay_frame(self, page):
        for frame in page.frames:
            if NP_EXT in frame.url and "video_overlay" in frame.url:
                return frame
        return None

    def process_page(self, state):
        page, ch = state["page"], state["channel"]
        if page.is_closed():
            return
        frame = self.overlay_frame(page)
        if not frame:
            state["phase"] = "Overlay not loaded"
            return
        try:
            state["note"] = ""
            banner = frame.locator("button#banner")
            text = " ".join(banner.inner_text(timeout=350).lower().split()) if banner.count() else ""
            shown = bool(banner.count() and banner.evaluate(
                "el => { const x=parseFloat(el.style.opacity); return (Number.isNaN(x) ? parseFloat(getComputedStyle(el).opacity) : x) > .1; }"
            ))
            joined = frame.locator("#giveaway-joined")
            joined_text = False
            if joined.count() > 0:
                joined_text = "giveaway joined" in joined.inner_text(timeout=350).lower() and joined.evaluate(
                    "el => { const x=parseFloat(el.style.opacity); return (Number.isNaN(x) ? parseFloat(getComputedStyle(el).opacity) : x) > 0; }"
                )
            prompt = shown and "card pack giveaway" in text and "click to join" in text
            if prompt and not state["active_banner"]:
                state["attempts"] = 0
                state["active_banner"] = True
            elif not prompt:
                state["active_banner"] = False
            if joined_text and not state["joined_text"]:
                state["overlay_join_at"] = time.time()
                if time.time() - state["last_server_join"] > 15:
                    self.bump(ch, "joined")
                state["phase"] = "Joined"
                self.log(ch, "Giveaway joined (confirmed by the overlay).", "ok")
            elif joined_text:
                state["phase"] = "Joined"
            elif state["pending_until"] > time.time():
                state["phase"] = "Joining"
            elif state["pending_until"]:
                state["pending_until"] = 0
                state["phase"] = "No join confirmation"
                self.log(ch, "No join confirmation; a single retry is available if the giveaway remains active.", "warn")
            elif prompt and state["attempts"] >= 2:
                state["phase"] = "No join confirmation"
            else:
                state["phase"] = state["note"] or "Waiting"
            state["joined_text"] = joined_text
            if shown and "giveaway ended" in text:
                body = " ".join(frame.locator("body").inner_text(timeout=500).split())[:1000]
                self.capture(ch, state, body)
                if LOSS.search(body) and state["outcome"] != "loss":
                    state["outcome"] = "loss"
                    self.bump(ch, "lost")
                    self.log(ch, "Giveaway ended without a win.", "info")
                if not state["dismissed"]:
                    state["dismissed"] = True
                    try:
                        frame.locator("#dismiss-button").click(timeout=500, force=True)
                        time.sleep(.2)
                        if "giveaway ended" in banner.inner_text(timeout=250).lower():
                            banner.click(timeout=500, force=True)
                    except Exception as e:
                        self.log(ch, f"Could not dismiss the ended giveaway: {e}", "warn")
            else:
                state["dismissed"] = False
                body = " ".join(frame.locator("body").inner_text(timeout=500).split())[:1000]
                self.capture(ch, state, body)
                if WIN.search(body) and state["outcome"] != "win":
                    state["outcome"] = "win"
                    self.bump(ch, "won")
                    self.log(ch, "Possible win detected from giveaway text. Check the stream to confirm.", "ok")
            if prompt and not joined_text and state["attempts"] < 2:
                if time.time() - state["last_click"] >= JOIN_GAP and not state["pending_until"]:
                    state["phase"] = "Joining"
                    state["last_click"] = time.time()
                    state["outcome"] = ""
                    state["attempts"] += 1
                    state["pending_until"] = time.time() + 8
                    banner.click(timeout=900, force=True)
                    self.log(ch, "Clicked the giveaway button; waiting for the server response.")
        except Exception as e:
            if "closed" not in str(e).lower() and "detached" not in str(e).lower():
                state["note"] = str(e)[:100]
        now = time.time()
        reloads = [t for t in state["reloads"] if now-t < 600]
        state["reloads"] = reloads
        if state.pop("got_401", False) and now-state["last_reload"] > 60 and len(reloads) < 3:
            state["last_reload"] = now
            state["reloads"].append(now)
            try:
                frame.evaluate("location.reload()")
                state["phase"] = "Refreshing login"
                self.log(ch, "Join returned 401; refreshing the giveaway overlay.", "warn")
            except Exception:
                pass
        elif state.get("got_401") and len(reloads) >= 3 and not state.get("auth_limit_logged"):
            state["got_401"] = False
            state["auth_limit_logged"] = True
            state["phase"] = "Login refresh limit reached"
            self.log(ch, "Repeated 401 responses; sign in again in the app's Edge window.", "bad")

    def bump(self, ch, key):
        item = self.stats.setdefault(ch, {"joined": 0, "won": 0, "lost": 0})
        item[key] = item.get(key, 0) + 1
        self.save_stats()
        self.emit("stats", stats=self.stats)

    def capture(self, ch, state, text):
        text = text.strip()
        if not text or text in state["captures"]:
            return
        if len(state["captures"]) >= 40:
            state["captures"].pop()
        state["captures"].add(text)
        self.emit("capture", row={"time": time.time(), "channel": ch, "text": text[:300]})

    def wake_tabs(self, pages):
        if not pages or self.waking:
            return
        self.waking = True
        self.wake_abort.clear()
        visible = pages[-1]
        try:
            for s in pages:
                try:
                    if not s["page"].is_closed() and s["page"].evaluate("document.visibilityState") == "visible":
                        visible = s
                        break
                except Exception:
                    continue
            for s in pages:
                if self.halt.is_set() or self.wake_abort.is_set():
                    break
                page = s["page"]
                if page.is_closed():
                    continue
                page.bring_to_front()
                self.wake_abort.wait(1.5)
            if not visible["page"].is_closed():
                visible["page"].bring_to_front()
            self.log("", f"Background tab wake cycle checked {len(pages)} channel(s).")
        except Exception as e:
            self.log("", f"Wake cycle stopped: {e}", "warn")
        finally:
            self.waking = False
            self.next_wake = time.time() + self.wake_minutes * 60

    def run(self):
        self.emit("ready")
        while not self.halt.is_set():
            try:
                while True:
                    cmd, value = self.commands.get_nowait()
                    if cmd == "launch": self.connect_edge()
                    elif cmd == "open": self.open_channels(value)
                    elif cmd == "focus":
                        for item in self.pages.values():
                            if item["channel"] == value and not item["page"].is_closed():
                                item["page"].bring_to_front()
                                break
                    elif cmd == "monitor": self.enabled = value
                    elif cmd == "wake": self.wake_enabled = value
                    elif cmd == "minutes": self.wake_minutes = value
                    elif cmd == "wake_now":
                        self.connect_edge()
                        self.wake_tabs(self.refresh_pages())
            except queue.Empty:
                pass
            except Exception as e:
                self.emit("error", message=str(e))
                self.log("", str(e), "bad")
            if self.context:
                try:
                    pages = self.refresh_pages()
                    if self.enabled:
                        for s in pages:
                            self.process_page(s)
                    if self.enabled and self.wake_enabled and time.time() >= self.next_wake:
                        self.wake_tabs(pages)
                    rows = [{"channel": s["channel"], "phase": s["phase"],
                             "joined": self.stats.get(s["channel"], {}).get("joined", 0),
                             "won": self.stats.get(s["channel"], {}).get("won", 0),
                             "lost": self.stats.get(s["channel"], {}).get("lost", 0),
                             "ready": self.overlay_frame(s["page"]) is not None}
                            for s in pages]
                    self.emit("pages", rows=rows, stats=self.stats,
                              wake="Waking tabs…" if self.waking else "")
                except Exception as e:
                    self.emit("error", message=str(e))
            self.halt.wait(1)
        try:
            if self.browser: self.browser.close()
            if self.play: self.play.stop()
        except Exception:
            pass
        if self.edge and self.edge.poll() is None:
            self.edge.terminate()

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("NoPixel Giveaway Clicker")
        self.root.geometry("820x650")
        self.events = queue.Queue()
        self.worker = BrowserWorker(self.events)
        self.worker.start()
        self.stats = {}
        self.captures = []
        self.ready_count = 0
        self.build()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(200, self.poll)

    def build(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Channels (comma or space separated):").pack(anchor="w")
        self.channels = ttk.Entry(top)
        self.channels.pack(fill="x", pady=4)
        row = ttk.Frame(top)
        row.pack(fill="x")
        ttk.Button(row, text="Open Edge", command=lambda: self.send("launch")).pack(side="left")
        ttk.Button(row, text="Open channels", command=self.open_channels).pack(side="left", padx=6)
        ttk.Button(row, text="Start monitoring", command=lambda: self.send("monitor", True)).pack(side="left")
        ttk.Button(row, text="Stop", command=lambda: self.send("monitor", False)).pack(side="left", padx=6)
        ttk.Button(row, text="Wake tabs now", command=lambda: self.send("wake_now")).pack(side="left")
        self.status = tk.StringVar(value="Starting…")
        ttk.Label(top, textvariable=self.status).pack(anchor="w", pady=(6, 0))

        settings = ttk.Frame(self.root, padding=(10, 0))
        settings.pack(fill="x")
        self.wake = tk.BooleanVar(value=False)
        ttk.Checkbutton(settings, text="Wake background tabs periodically",
                        variable=self.wake, command=lambda: self.send("wake", self.wake.get())).pack(side="left")
        ttk.Label(settings, text="Every (minutes):").pack(side="left", padx=(10, 4))
        self.minutes = tk.StringVar(value="3")
        ttk.Spinbox(settings, from_=1, to=30, width=4, textvariable=self.minutes,
                    command=self.set_minutes).pack(side="left")
        self.minutes.trace_add("write", lambda *_: self.set_minutes())

        statsbox = ttk.LabelFrame(self.root, text="Channels", padding=8)
        statsbox.pack(fill="both", expand=True, padx=10, pady=8)
        self.table = ttk.Treeview(statsbox, columns=("channel", "state", "joins", "wins", "losses"), show="headings", height=8)
        for col, title, width in (("channel", "Channel", 180), ("state", "Status", 280),
                                  ("joins", "Joins", 70), ("wins", "Wins", 60), ("losses", "Losses", 70)):
            self.table.heading(col, text=title)
            self.table.column(col, width=width, anchor="w")
        self.table.pack(fill="both", expand=True)
        self.table.bind("<Double-1>", self.focus_channel)

        self.totals = tk.StringVar(value="Watching: 0    Ready: 0    Joins: 0    Wins: 0    Losses: 0")
        ttk.Label(self.root, textvariable=self.totals, padding=(10, 0)).pack(anchor="w")
        box = ttk.LabelFrame(self.root, text="Activity log", padding=8)
        box.pack(fill="both", expand=True, padx=10, pady=8)
        actions = ttk.Frame(box)
        actions.pack(fill="x", pady=(0, 4))
        ttk.Button(actions, text="Copy captures", command=self.copy_captures).pack(side="left")
        ttk.Button(actions, text="Clear log", command=self.clear_log).pack(side="left", padx=6)
        self.log = tk.Text(box, height=11, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True)

    def send(self, cmd, value=None):
        if (cmd == "monitor" and not value) or (cmd == "wake" and not value):
            self.worker.wake_abort.set()
        self.worker.commands.put((cmd, value))

    def focus_channel(self, event):
        row = self.table.identify_row(event.y)
        if row:
            self.send("focus", self.table.item(row, "values")[0])

    def copy_captures(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(json.dumps(self.captures[-40:], indent=2, ensure_ascii=False))
        self.status.set(f"Copied {min(40, len(self.captures))} overlay capture(s).")

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def set_minutes(self):
        try:
            self.send("minutes", max(1, min(30, int(self.minutes.get()))))
        except ValueError:
            pass

    def open_channels(self):
        names = re.findall(r"[a-zA-Z0-9_]{3,25}", self.channels.get())
        if not names:
            messagebox.showinfo("Channels", "Enter one or more Twitch channel names first.")
            return
        self.send("open", list(dict.fromkeys(n.lower() for n in names)))

    def add_log(self, row):
        self.log.configure(state="normal")
        tm = time.strftime("%H:%M:%S", time.localtime(row["time"]))
        label = f'[{tm}] {row["channel"]}: ' if row["channel"] else f'[{tm}] '
        self.log.insert("1.0", label + row["message"] + "\n")
        self.log.delete("250.0", "end")
        self.log.configure(state="disabled")

    def poll(self):
        try:
            while True:
                e = self.events.get_nowait()
                if e["type"] == "status": self.status.set(e["text"])
                elif e["type"] == "ready": self.status.set("Open Edge and sign in to Twitch to get started.")
                elif e["type"] == "error": self.status.set(e["message"])
                elif e["type"] == "log": self.add_log(e["row"])
                elif e["type"] in ("pages", "stats"):
                    self.stats = e.get("stats", self.stats)
                    if e["type"] == "pages":
                        ready = sum(r["ready"] for r in e["rows"])
                        self.ready_count = ready
                        self.status.set(e.get("wake") or f'{len(e["rows"])} channel(s) · {ready} giveaway widget(s) ready · monitoring {"on" if self.worker.enabled else "off"}')
                        for item in self.table.get_children(): self.table.delete(item)
                        for r in e["rows"]:
                            self.table.insert("", "end", values=(r["channel"], r["phase"], r["joined"], r["won"], r["lost"]))
                    self.update_totals()
                elif e["type"] == "capture":
                    self.captures.append(e["row"])
                    self.add_log({"time": e["row"]["time"], "channel": e["row"]["channel"],
                                  "message": "Overlay: " + e["row"]["text"][:120], "level": "info"})
        except queue.Empty:
            pass
        self.root.after(200, self.poll)

    def update_totals(self):
        vals = list(self.stats.values())
        self.totals.set(f'Watching: {len(self.table.get_children())}    Ready: {self.ready_count}    Joins: {sum(v.get("joined",0) for v in vals)}    Wins: {sum(v.get("won",0) for v in vals)}    Losses: {sum(v.get("lost",0) for v in vals)}')

    def close(self):
        self.worker.halt.set()
        self.root.destroy()

if __name__ == "__main__":
    app = App()
    app.root.mainloop()
