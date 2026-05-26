# Spiral Search Bridge

Cross-platform spiral-search automation for **ASCOM Alpaca**–compatible
telescope mounts. Point your mount at the expected coordinates, press
**Start**, and the app drives an expanding spiral search pattern until your
target comes into view. You control everything from a browser on a laptop,
tablet, or phone — including phone **tilt-to-steer** for fine centering, with
a dead-man's switch so nothing moves unless your thumb says so.

Runs on Windows, macOS, and Linux as a self-contained executable — no .NET
runtime or installer required.

## 📦 Download

Get the binaries from the **[`spiralsearch-v2.0` release →](../../releases/tag/spiralsearch-v2.0)**.
Pick the asset that matches your machine:

| Asset | Platform |
|---|---|
| `SpiralSearch-Bridge-v2.0-win-x86.zip` | Windows (32- and 64-bit) |
| `SpiralSearch-Bridge-v2.0-macos-arm64.zip` | macOS Apple Silicon (M1–M4) |
| `SpiralSearch-Bridge-v2.0-macos-x64.zip` | macOS Intel |
| `SpiralSearch-Bridge-v2.0-linux-arm64.zip` | Linux ARM64 (Raspberry Pi 4/5) |

Each zip is a self-contained single-file executable plus the User Manual. No
.NET runtime installation is required — just unzip and run.

## Quick start

1. **Run it.** Unzip and launch `SpiralSearch.Bridge` (`.exe` on Windows). On
   macOS, first-time only, from Terminal in the unzipped folder:
   ```bash
   sudo xattr -cr .
   chmod +x SpiralSearch.Bridge
   codesign --force --deep --sign - SpiralSearch.Bridge
   ./SpiralSearch.Bridge
   ```
   (The ad-hoc `codesign` step is required on Apple Silicon.) On Linux,
   `chmod +x SpiralSearch.Bridge` once, then `./SpiralSearch.Bridge`.
2. **Open the UI.** Same computer: <https://localhost:5056>. From a phone or
   another device on your network: `https://<server-ip>:5056` (the console
   prints the LAN address at startup).
   > Phones **must** use HTTPS (`:5056`) — iOS and Android require a secure
   > connection for the motion sensors used by tilt steering. First time,
   > install the certificate from `http://<server-ip>:5055/install` in Safari.
3. **Connect your mount.** In the **Alpaca Server** panel, click **Discover**
   (or enter host/port `11111` and **Apply**), then **Unpark** and **Track On**.
4. **Search.** Slew to the expected target, set FOV / dwell / step fraction,
   and click **Start**. Use Pause/Resume, Stop, or Restart Origin as needed.

The full **[User Manual](User_Manual.txt)** in this branch documents every
control — FOV calculators, camera presets, tilt steering, certificate setup,
safety guards, the REST API, and troubleshooting.

## Notes

- **Distribution:** This branch and the release carry the pre-built binaries
  and documentation only. The application source is maintained privately.
- **Requirements:** An ASCOM Alpaca server (e.g. ASCOM Remote, the ASCOM
  Platform's Alpaca server, or a simulator) connected to your mount, reachable
  on the same network. For tilt steering, a phone with a gyroscope on the same
  Wi-Fi.

---

Copyright © 2026 Wes McDonald. All rights reserved.
