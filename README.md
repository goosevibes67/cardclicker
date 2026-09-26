# Card Clicker

A Windows color-based auto-clicker. A ready-to-run package is built as one ZIP containing a standalone app; end users do not need Python or a command prompt.

## Use the packaged app

The ready-to-run package is `Auto Clicker.zip`. The build script below creates it in `release`; attach that ZIP to a GitHub Release to publish it on the [Releases page](https://github.com/goosevibes67/cardclicker/releases). Then follow the included `QUICK_START.txt`:

1. Extract the ZIP and open the extracted `Auto Clicker` folder.
2. Double-click `Create Desktop Shortcut.vbs` to create `Auto Clicker.lnk`.
3. Drag `Auto Clicker.lnk` to the Desktop.
4. Double-click the Desktop shortcut.

The app opens stopped. Click **Start** to scan immediately, click at most one target, update both previews, and repeat after 10 seconds. Click **Stop** to pause. The GUI briefly hides during each capture so it won't detect its own preview.

## Run from source

Use this section only if you want to run or edit the Python code. The source download is not the ready-to-run app.

1. Install Python 3 for Windows.
2. Open the project folder in File Explorer. Click its address bar, type `powershell`, and press Enter. This opens PowerShell in the project folder.
3. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Run the GUI:

   ```powershell
   python auto_clicker.py
   ```

For a fast preview that never clicks, run `python auto_clicker.py --debug`. It refreshes about twice per second. Click the screen preview to print a pixel's HSV value; press `q` to close it.

## Build the ZIP

From PowerShell opened in the project folder, run:

```powershell
.\package_release.ps1
```

The script creates `release\Auto Clicker.zip`. It installs its pinned build tool and app dependencies into a temporary environment, then packages the app as a single Windows executable. The ZIP is build output; attach it to a GitHub Release for end-user downloads. Do not use **Code > Download ZIP** as the app download; that contains source code only.

## Detection settings

Edit the constants near the top of `auto_clicker.py`:

| Setting | Purpose |
|---|---|
| `PINK_LOWER`, `PINK_UPPER` | HSV color range. Use debug mode to sample a pixel. |
| `MIN_BLOB_AREA` | Minimum matching area in pixels. |
| `SCAN_REGION` | Optional `(left, top, width, height)` crop; `None` scans the full screen. |
| `CHECK_INTERVAL` | Seconds between GUI scans; default is 10. |
| `CLICK_JITTER_PX` | Maximum random offset from the detected center. |

Each screenshot is converted to HSV, filtered to the chosen color, and cleaned to remove specks and fill small gaps. Small regions are ignored; the largest remaining region is clicked at its center with a small random offset. No match means no click. PyAutoGUI's upper-left-corner fail-safe remains enabled.
