# Card Clicker

A Windows desktop helper for NoPixel card giveaways on Twitch. It drives a dedicated Microsoft Edge profile and reads the giveaway widget in Twitch's page frames, so it does not install or require a browser extension. It can watch open channel tabs, attempt to join when the giveaway button appears, confirm joins from the server response or overlay, track likely win/loss text, and try to dismiss the ended giveaway panel.

## Download and run

Download **NoPixel Giveaway Clicker.zip** from the repository's [Releases page](https://github.com/goosevibes67/cardclicker/releases), extract it, run **Create Desktop Shortcut.vbs**, and drag the shortcut it creates to your Desktop. Keep the extracted folder in place. Launch the shortcut, click **Open Edge**, and sign in to Twitch in the new Edge profile. This profile is separate from your normal Edge profile and is kept on your computer. Add channel names in the app and click **Open channels**, then **Start monitoring**.

Keep Edge open and signed in while monitoring. You can also open channel tabs manually in that Edge window. The app only monitors Twitch channel pages that are open in its dedicated Edge profile. The optional background-tab wake feature briefly brings each monitored page forward; it is off by default.

## What the app can and cannot tell

- A successful `POST /channel/giveaway/join` response is counted as a confirmed join. A visible “giveaway joined” overlay is also used as fallback confirmation.
- A 401 response triggers a rate-limited reload of the NoPixel overlay to refresh its session.
- Win/loss counts are inferred from visible giveaway wording. Treat “possible win” as a prompt to check the stream; wording can change.
- Activity and per-channel counts are stored locally under `%LOCALAPPDATA%\CardClicker`.
- The app does not read or display Twitch passwords or extract tokens. Twitch sign-in happens in Edge.

This is an independent community project, not affiliated with Twitch or NoPixel. Check the giveaway and platform rules before using automation.

## Run from source

Install Python 3.10 or newer, open PowerShell in the project folder, then run:

```powershell
python -m pip install -r requirements.txt
python auto_clicker.py
```

Microsoft Edge must be installed. The first app launch creates its dedicated Edge profile under `%LOCALAPPDATA%\CardClicker\EdgeProfile`; sign into Twitch there once. No separate Playwright browser download is needed.

The former color-based desktop clicker is preserved as `color_clicker.py`. To run it from source, install `requirements-color-clicker.txt` and run `python color_clicker.py`.

## Build a release package

From PowerShell in the project folder, run:

```powershell
.\package_release.ps1
```

This builds `release\NoPixel Giveaway Clicker.zip`, which is the ready-to-run app package. Attach that ZIP to a GitHub Release. **Code → Download ZIP** contains source code, not the app.
