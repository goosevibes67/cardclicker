# auto-clicker

A small color-based auto-clicker for Windows. Every 10 seconds it takes a
screenshot, looks for the largest blob matching a target color, and clicks
its center once.

## Setup

```
pip install -r requirements.txt
```

## Usage

Run it:

```
python auto_clicker.py
```

Press `Ctrl+C` to stop.

### Debug mode

```
python auto_clicker.py --debug
```

Opens two live preview windows:

- **screen** — the screen with a green box drawn around anything that
  would currently be clicked.
- **mask** — the raw black/white result of the color filter, with no
  boxes, so you can see exactly what is and isn't passing.

Both rescan every ~0.5 seconds so you can watch it live (this is faster
than the real 10s interval — it's just for tuning, not a preview of the
real click timing). Click anywhere on the **screen** window to print that
pixel's HSV value to the console — useful for figuring out why something
unexpected is (or isn't) being detected. Press `q` to close both windows.

## How it works

1. **Screenshot → HSV.** `pyautogui.screenshot()` grabs the screen. Matching
   is done in HSV (Hue/Saturation/Value) rather than RGB, since HSV
   separates *what color it is* from *how bright/washed-out it is*, which
   makes matching robust to small lighting/compression differences.
2. **Color mask.** `cv2.inRange()` turns the screenshot into black/white:
   white wherever a pixel falls inside `PINK_LOWER`–`PINK_UPPER`, black
   everywhere else. A couple of `cv2.morphologyEx` passes clean up the
   mask — removing small stray specks and filling small gaps so a real
   target reads as one solid blob.
3. **Find blobs.** `cv2.findContours` traces every white region. Anything
   under `MIN_BLOB_AREA` is discarded as noise; for what's left,
   `cv2.moments` gives the centroid (the click point).
4. **Click.** Once per 10-second round, the largest match found gets
   clicked, with a small random pixel offset (`CLICK_JITTER_PX`) so clicks
   aren't pixel-identical every time.

## Configuration

All of these are constants near the top of `auto_clicker.py`:

| Constant | Meaning |
|---|---|
| `PINK_LOWER` / `PINK_UPPER` | HSV range to match. Use `--debug` and click a pixel to read off its HSV, then adjust. |
| `MIN_BLOB_AREA` | Minimum pixel area for a match to count. |
| `SCAN_REGION` | `(left, top, width, height)` to limit the screenshot area, or `None` for the full screen. Narrowing this is the biggest performance win if scanning ever feels slow. |
| `CHECK_INTERVAL` | Seconds between screenshots (default `10.0`). |
| `CLICK_JITTER_PX` | Max random pixel offset applied to each click. |

## Notes

- Windows only, due to `pyautogui`'s coordinate/click handling assumptions
  used here (screenshotting itself is cross-platform).
- Only meant for clicking your own fixed on-screen targets (e.g. a
  recurring banner/prompt) — it has no image recognition beyond flat color
  matching, so it isn't suited to distinguishing similarly-colored but
  different UI elements.
