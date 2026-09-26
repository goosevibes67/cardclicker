"""
Minimal color-based auto-clicker for Windows.

Every 10 seconds it takes one screenshot, looks for the largest blob
matching a target color, and clicks its center once.

  --debug   Live preview: rescans every ~0.5s (independent of the 10s
            live-run interval), drawing a green box around anything it
            would click. Click the "screen" window to print that
            pixel's HSV to the console. Press 'q' to quit.

SETUP
  pip install -r requirements.txt

Ctrl+C to stop.
"""

import sys
import time
import random
import numpy as np
import cv2
import pyautogui

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
        targets.append((cx, cy, x + offset_x, y + offset_y, w, h))
    return targets, frame, mask


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


def main():
    print("Running. Ctrl+C to stop.")
    while True:
        targets, _, _ = scan()
        if targets:
            cx, cy, *_ = targets[0]
            x = cx + random.randint(-CLICK_JITTER_PX, CLICK_JITTER_PX)
            y = cy + random.randint(-CLICK_JITTER_PX, CLICK_JITTER_PX)
            pyautogui.click(x, y)
            print(f"Clicked ({x}, {y})")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    if "--debug" in sys.argv:
        debug_once()
    else:
        try:
            main()
        except KeyboardInterrupt:
            print("Stopped.")
