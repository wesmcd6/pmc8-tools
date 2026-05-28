# PMC-Eight&trade; Tools

Downloads for **Explore Scientific&trade; PMC-Eight&trade;** telescope mount users — the **ExploreStars Envision&trade;** mount-control app, ESP32 Wi-Fi firmware tools, and the latest Propeller firmware.

> 📖 **New here?** Start with [**GETTING_STARTED.txt**](GETTING_STARTED.txt) —
> a step-by-step guide that walks you through choosing the right tool,
> updating firmware, and installing ExploreStars Envision in the correct order.
> First-time users should read this before anything else. Experienced
> users can jump to its "Quick Reference" section.

## ExploreStars Envision&trade; — current

📦 **[Get the v2.4.0.0 release →](../../releases/tag/v2.4.0.0)**

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

## Network Configuration

**[Configure PMC8 for Home Network Connection](../../tree/home-network-config)** — a
Windows utility that puts a PMC-Eight WiFi module (**ESP32 / ESP8266 / RN-131**)
onto your home network over USB serial, so the mount joins your router and gets
a LAN IP. 📦 **[Download the v1.0 release](../../releases/tag/home-network-config-v1.0)**
— `Configure-PMC8-Home-Network-v1.0.exe`, a single self-contained executable
(no installer, no .NET install needed).

## Spiral Search Bridge

Cross-platform spiral-search automation for **ASCOM Alpaca**–compatible mounts. Point at the expected coordinates, press **Start**, and the mount runs an expanding spiral search pattern until your target appears. Browser-based UI with phone **tilt-to-steer** for fine centering. 📦 **[Download the v2.0 release →](../../releases/tag/spiralsearch-v2.0)**

| Item | Link | Notes |
|---|---|---|
| README and User Manual | [`spiral-search`](../../tree/spiral-search) | Setup, FOV calculators, tilt steering, REST API, troubleshooting |
| Windows ZIP | [`SpiralSearch-Bridge-v2.0-win-x86.zip`](../../releases/tag/spiralsearch-v2.0) | 32- and 64-bit; extract and run `SpiralSearch.Bridge.exe` |
| macOS ZIP (Apple Silicon) | [`SpiralSearch-Bridge-v2.0-macos-arm64.zip`](../../releases/tag/spiralsearch-v2.0) | M1–M4; ad-hoc codesign on first run (see manual) |
| macOS ZIP (Intel) | [`SpiralSearch-Bridge-v2.0-macos-x64.zip`](../../releases/tag/spiralsearch-v2.0) | Intel Macs |
| Linux ARM64 ZIP | [`SpiralSearch-Bridge-v2.0-linux-arm64.zip`](../../releases/tag/spiralsearch-v2.0) | Raspberry Pi 4/5 |

Each zip is a self-contained single-file executable plus the User Manual — no .NET runtime or installer required.

## Firmware Tools

| Tool | Branch | Description |
|------|--------|-------------|
| PMC-Eight UFCT | [`pmc8-ufct`](../../tree/pmc8-ufct) | **Universal Firmware Configuration Tool** (Windows) — read/write config, send raw commands, serial firmware flash, RN-131 restore |
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

ExploreStars Envision&trade; is an independent application that controls Explore Scientific&trade; PMC-Eight&trade; telescope mounts. The application code and project materials are authored and owned by Wes McDonald. If Explore Scientific, LLC recommends, endorses, promotes, or distributes the app, that should be understood as support for an independently authored application within the PMC-Eight&trade; ecosystem, not as Explore Scientific authorship or ownership of the app.

Copyright © 2026 Wes McDonald. All rights reserved.

## Support

For questions about the PMC-Eight mount itself, visit [Explore Scientific](https://www.explorescientific.com).
