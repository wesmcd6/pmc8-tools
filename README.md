# PMC-Eight Tools

Downloads for Explore Scientific PMC-Eight telescope mount users.

## Branches

| Branch | Contents |
|--------|----------|
| [`explorestars-lite`](../../tree/explorestars-lite) | ExplorestarsLite Android APK — standalone telescope control app |
| [`esp32-ota`](../../tree/esp32-ota) | ESP32 OTA firmware update script, binary, and quick start guide |

---

## ExplorestarsLite — Android App

Switch to the **[explorestars-lite](../../tree/explorestars-lite)** branch to download.

- Controls PMC-Eight mounts via ESP32 WiFi bridge (no PC needed)
- Catalog search, GoTo, tracking, spiral search, sync, meridian flip
- Works in ESP32 AP mode (192.168.47.1) or on your home WiFi LAN

### Install

1. Go to the [explorestars-lite branch](../../tree/explorestars-lite) and download the APK
2. Tap to install on your Android phone (allow "Install from unknown sources" if prompted)
3. If Play Protect blocks it, tap "Install anyway"
4. Open the app, go to Setup, enter your mount's IP address, and tap Connect

## ESP32 OTA Firmware Update

Switch to the **[esp32-ota](../../tree/esp32-ota)** branch to download.

Update your PMC-Eight's ESP32 firmware over WiFi — no serial cable or jumpers needed.

### Prerequisites

- Python 3.x installed on your PC
- `pip install pyserial`
- USB serial connection to the PMC-Eight (COM port)
- PMC-Eight powered on with Propeller firmware running

See `OTA_QUICK_START_V2.txt` on the esp32-ota branch for detailed instructions.

## Support

For questions about the PMC-Eight mount, visit the [Explore Scientific PMC-Eight forum](https://www.explorescientific.com).
