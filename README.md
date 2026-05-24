# PMC-Eight&trade; Tools

Downloads for **Explore Scientific&trade; PMC-Eight&trade;** telescope mount users — the **ExploreStars Envision&trade;** mount-control app, ESP32 Wi-Fi firmware tools, and the latest Propeller firmware.

> 📖 **New here?** Start with [**GETTING_STARTED.txt**](GETTING_STARTED.txt) —
> a step-by-step guide that walks you through choosing the right tool,
> updating firmware, and installing ExploreStars Envision in the correct order.
> First-time users should read this before anything else. Experienced
> users can jump to its "Quick Reference" section.

## ExploreStars Envision&trade; — current

📦 **[Get the latest release →](../../releases/latest)**

The Releases page carries pre-built binaries for every platform. Pick the asset that matches your device:

| Asset name | Platform | Notes |
|---|---|---|
| `ExploreStars-Envision-vX.Y.Z.W-android.apk` | Android | Sideload — tap to install |
| `ExploreStars-Envision-vX.Y.Z.W-windows.zip` | Windows | Extract, run `ExplorestarsLite.Maui.exe` |
| `ExploreStars-Envision-vX.Y.Z.W-pwa-server.zip` | Self-hosted PWA | Run on a Windows/Mac/Linux PC; phones connect via local Wi-Fi |

For the user manual and attribution doc, see the [`explorestars-envision`](../../tree/explorestars-envision) branch.

iOS and macOS app-store builds are planned.


## PMC8 Dashboard

**Downloads:** use the `pmc8-dashboard-v0.1.0` release assets when available.

PMC8 Dashboard is a Python/PyQt6 desktop utility for PMC-Eight configuration, command testing, response logging, and firmware upload workflow support.

| Item | Link | Notes |
|---|---|---|
| Source and manual | [`pmc8-dashboard`](../../tree/pmc8-dashboard/pmc8-dashboard) | Public source, docs, and third-party notices |
| Windows ZIP | [`PMC8_Dashboard_Windows.zip`](../../releases/tag/pmc8-dashboard-v0.1.0) | Extract and run `run_dashboard_windows.bat` |
| macOS ZIP | [`PMC8_Dashboard_macOS.zip`](../../releases/tag/pmc8-dashboard-v0.1.0) | Extract, `chmod +x run_dashboard_macos.command`, then `./run_dashboard_macos.command` if needed |

## Firmware Tools

| Tool | Branch | Description |
|------|--------|-------------|
| PMC-Eight Firmware | [`pmc8-firmware`](../../tree/pmc8-firmware) | Latest Propeller firmware (flash via UFCT) |
| ESP32 OTA Update | [`esp32-ota`](../../tree/esp32-ota) | Wi-Fi firmware update script + binary |
| ESP32 Serial Flash | [`esp32-serial-flash`](../../tree/esp32-serial-flash) | Fallback when OTA isn't possible — self-contained zip with ESPLoader + esptool |

## Alternate distribution branches

| Branch | What it carries |
|---|---|
| [`pwa-server`](../../tree/pwa-server) | Pre-built PWA server distribution (alternate to the Release zip — same content) |
| [`windows`](../../tree/windows) | Windows desktop binary (alternate to the Release zip — same content) |

## About ExploreStars Envision&trade;

Cross-platform telescope mount control — runs on Android, Windows, and as a self-hosted PWA accessible from any phone or tablet on your local network.

- 11,000+ object catalog with altitude-based visibility coloring
- GoTo, Sync, Tracking (Sidereal/Solar/Lunar), Meridian Flip, multi-star alignment
- **Model-aware display** — chart marker and RA/Dec readouts can show the alignment-corrected "true sky" position
- **Star Seeker** in-app sky chart with sensor-based push-to identification
- **Camera field-of-view** overlay on the sky chart, with a calculator — sensor/camera presets, Barlow/reducer, and rotator-angle support
- Spiral Search, Thumb Pad centering with Fine/Coarse rates
- Solar system targets: planets, Moon, Sun, minor planets
- Multi-language UI (English, 简体中文, Français, Italiano, Español, Deutsch, Português, 日本語, Nederlands, Polski, Українська)
- Night vision mode for dark adaptation
- GPS location, firmware config reader/writer
- Works alongside Alpaca/ASCOM and planetarium software
- Built-in user manual

## Trademarks &amp; copyright

ExploreStars Envision&trade; is a trademark of Wes McDonald. Explore Scientific&trade;, ExploreStars&trade;, and PMC-Eight&trade; are trademarks of [Explore Scientific, LLC](https://www.explorescientific.com), and are used here with acknowledgement.

ExploreStars Envision&trade; is an independent application that controls Explore Scientific&trade; PMC-Eight&trade; telescope mounts. It is not produced or endorsed by Explore Scientific, LLC.

Copyright © 2026 Wes McDonald. All rights reserved.

## Support

For questions about the PMC-Eight mount itself, visit [Explore Scientific](https://www.explorescientific.com).
