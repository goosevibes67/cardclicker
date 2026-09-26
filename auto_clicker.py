"""
Minimal color-based auto-clicker for Windows.

Every 10 seconds it takes one screenshot, looks for the largest blob
matching a target color, and clicks its center once.

  --debug   Live preview: rescans every ~0.5s (independent of the 10s
            live-run interval), drawing a green box around anything it
            would click. Click the "screen" window to print that
            pixel's HSV to the console. Press 'q' to quit.

Default mode opens a GUI. Start scans immediately, then once every 10s;
the screen preview updates from those same scans. Stop pauses the loop.

SETUP
  pip install -r requirements.txt

Use the GUI's Stop button to pause.
"""

import sys
import random
import numpy as np
import cv2
import pyautogui
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

# ---- COLOR RANGE (HSV) ----
# Target color: #fb3f7c -> RGB (251, 63, 124) -> HSV (170, 191, 251).
# Upper hue capped at 176, not 179: values near 179 wrap around to true red
# (hue 0), which is what red police-light glare was matching.
PINK_LOWER = np.array([164, 140, 195])
PINK_UPPER = np.array([176, 255, 255])

MIN_BLOB_AREA = 8000          # ignore blobs smaller than this (pixels)
SCAN_REGION = None            # (left, top, width, height), or None for full screen
CHECK_INTERVAL = 10.0         # seconds between screenshots
CLICK_JITTER_PX = 3           # small random offset so clicks aren't pixel-identical


def scan():
    """Take one screenshot and return (targets, frame, mask), where targets
    is a list of (cx, cy, x, y, w, h) — center plus bounding box."""
    screenshot = pyautogui.screenshot(region=SCAN_REGION)
    frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    mask = cv2.inRange(hsv, PINK_LOWER, PINK_UPPER)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    offset_x, offset_y = (SCAN_REGION[0], SCAN_REGION[1]) if SCAN_REGION else (0, 0)

    targets = []
    for c in contours:
        if cv2.contourArea(c) < MIN_BLOB_AREA:
            continue
        M = cv2.moments(c)
        if M["m00"] == 0:
            continue
        x, y, w, h = cv2.boundingRect(c)
        cx = int(M["m10"] / M["m00"]) + offset_x
        cy = int(M["m01"] / M["m00"]) + offset_y
        targets.append((cv2.contourArea(c), (cx, cy, x + offset_x, y + offset_y, w, h)))
    targets.sort(key=lambda item: item[0], reverse=True)
    return [target for _, target in targets], frame, mask


def debug_once():
    win = "Debug: screen (green box = would click) - 'q' to quit, click to sample HSV"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, 640, 360)
    cv2.namedWindow("Debug: mask", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Debug: mask", 320, 180)

    last_frame = {"hsv": None}

    def on_click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and last_frame["hsv"] is not None:
            h, s, v = last_frame["hsv"][y, x]
            print(f"Clicked ({x}, {y}): HSV = ({h}, {s}, {v})")

    cv2.setMouseCallback(win, on_click)

    while True:
        targets, frame, mask = scan()
        last_frame["hsv"] = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        for cx, cy, x, y, w, h in targets:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
        print(f"Found {len(targets)} match(es): {[(cx, cy) for cx, cy, *_ in targets]}")
        cv2.imshow(win, frame)
        cv2.imshow("Debug: mask", mask)
        if cv2.waitKey(500) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()


class AutoClickerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Auto Clicker")
        self.running, self.next_scan = False, None
        self.status = tk.StringVar(value="Stopped")
        controls = ttk.Frame(self.root, padding=8)
        controls.pack(fill="x")
        ttk.Button(controls, text="Start", command=self.start).pack(side="left")
        ttk.Button(controls, text="Stop", command=self.stop).pack(side="left", padx=6)
        ttk.Label(controls, textvariable=self.status).pack(side="left", padx=8)
        previews = ttk.Frame(self.root, padding=8)
        previews.pack()
        self.screen = ttk.Label(previews, text="Screen preview")
        self.screen.grid(row=0, column=0, padx=4)
        self.mask = ttk.Label(previews, text="Color mask")
        self.mask.grid(row=0, column=1, padx=4)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def start(self):
        if not self.running:
            self.running = True
            self.scan_now()

    def stop(self):
        self.running = False
        if self.next_scan:
            self.root.after_cancel(self.next_scan)
            self.next_scan = None
        self.status.set("Stopped")

    def scan_now(self):
        if not self.running:
            return
        self.status.set("Scanning…")
        self.root.update_idletasks()
        self.root.withdraw()
        self.root.update()
        try:
            targets, frame, mask = scan()
            for cx, cy, x, y, w, h in targets:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
            if targets:
                cx, cy, *_ = targets[0]
                x = cx + random.randint(-CLICK_JITTER_PX, CLICK_JITTER_PX)
                y = cy + random.randint(-CLICK_JITTER_PX, CLICK_JITTER_PX)
                pyautogui.click(x, y)
                message = f"Clicked ({x}, {y})"
            else:
                message = "No match found"
        except Exception as error:
            self.running = False
            self.status.set(f"Scan failed: {error}")
            return
        finally:
            self.root.deiconify()
        self.show_preview(self.screen, frame, True, 640, 360)
        self.show_preview(self.mask, mask, False, 360, 360)
        self.status.set(f"{message} · next scan in {CHECK_INTERVAL:g}s")
        self.next_scan = self.root.after(int(CHECK_INTERVAL * 1000), self.scan_now)

    @staticmethod
    def show_preview(label, image, color, max_width, max_height):
        height, width = image.shape[:2]
        scale = min(max_width / width, max_height / height)
        size = (int(width * scale), int(height * scale))
        if color:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        photo = ImageTk.PhotoImage(Image.fromarray(cv2.resize(image, size)))
        label.configure(image=photo, text="")
        label.image = photo

    def close(self):
        self.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    if "--debug" in sys.argv:
        debug_once()
    else:
        AutoClickerGUI().run()
