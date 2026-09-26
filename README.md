# Auto Clicker

A small Windows utility that looks for a target color on screen and clicks the center of the largest matching area.

## Setup

Install Python 3, then install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Run

Open the GUI:

```powershell
python auto_clicker.py
```

Click **Start** to scan immediately. The app takes one screenshot, clicks at most once, updates both previews, and repeats after 10 seconds. **Stop** pauses the loop. The window briefly hides during each scan so it cannot detect its own preview. It starts stopped.

The screen preview marks detected targets with green boxes and red center dots. The mask preview shows which pixels passed the color filter. The status line reports the match count and click result.

## Debug preview

```powershell
python auto_clicker.py --debug
```

Debug mode opens a screen preview and a black-and-white color mask. It refreshes every 0.5 seconds and never clicks. Click the screen preview to print the sampled pixel's HSV value; press `q` to close the windows.

## How detection works

1. Capture the screen and convert it from RGB to HSV.
2. Keep pixels inside the configured HSV range; clean small specks and gaps with OpenCV morphology filters.
3. Find connected color regions and ignore anything smaller than `MIN_BLOB_AREA`.
4. Sort matches by area, then click the center of the largest match with up to 3 pixels of jitter. If nothing matches, the app does not click.

## Settings

Edit the constants near the top of `auto_clicker.py`:

| Setting | Purpose |
|---|---|
| `PINK_LOWER`, `PINK_UPPER` | HSV range to detect. Use debug mode to sample a pixel. |
| `MIN_BLOB_AREA` | Minimum matching area in pixels. |
| `SCAN_REGION` | Optional `(left, top, width, height)` crop; `None` scans the full screen. |
| `CHECK_INTERVAL` | Seconds between GUI scans; default is 10. |
| `CLICK_JITTER_PX` | Maximum random offset from the detected center. |

PyAutoGUI's corner fail-safe remains enabled: move the pointer to the upper-left corner to interrupt a click operation. Use this only with targets you intend to click; color matching can also detect unrelated areas with similar colors.
