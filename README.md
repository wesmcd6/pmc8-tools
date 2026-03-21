# PMC-Eight Tools

Downloads for Explore Scientific PMC-Eight telescope mount users.

## ExplorestarsLite — Android App

**`com.explorestarlite.app-Signed.apk`** — Standalone telescope control app for Android phones.

- Controls PMC-Eight mounts via ESP32 WiFi bridge (no PC needed)
- Catalog search, GoTo, tracking, spiral search, sync, meridian flip
- Works in ESP32 AP mode (192.168.47.1) or on your home WiFi LAN

### Install

1. Download the APK to your Android phone
2. Tap to install (allow "Install from unknown sources" if prompted)
3. If Play Protect blocks it, tap "Install anyway"
4. Open the app, go to Setup, enter your mount's IP address, and tap Connect

## ESP32 OTA Firmware Update

Update your PMC-Eight's ESP32 firmware over WiFi — no serial cable or jumpers needed.

### Files

| File | Description |
|------|-------------|
| `ota_update_v2.py` | Python script — handles the full OTA process |
| `esp-at.bin` | ESP32 AT firmware binary (OTA-compatible, ~1.5 MB) |
| `OTA_QUICK_START_V2.txt` | Step-by-step instructions |

### Prerequisites

- Python 3.x installed on your PC
- `pip install pyserial`
- USB serial connection to the PMC-Eight (COM port)
- PMC-Eight powered on with Propeller firmware running

### Quick Start

```
python ota_update_v2.py --help
```

See `OTA_QUICK_START_V2.txt` for detailed instructions. The script supports two modes:
- **Direct (AP mode)** — PC connected to the PMC-8's own WiFi network
- **LAN mode** — PC and PMC-8 both on your home WiFi

## Support

For questions about the PMC-Eight mount, visit the [Explore Scientific PMC-Eight forum](https://www.explorescientific.com).
