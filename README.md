# PMC-Eight ESP32 OTA Update

Update your PMC-Eight's ESP32 firmware **over-the-air** — no opening the
enclosure, no hex wrench, no jumper, no risk to the fragile Wi-Fi antenna
cable. This is the **simplest** way to update the ESP32 firmware.

If OTA isn't possible (ESP32 has no firmware, has corrupted firmware, or
has firmware too old to support OTA), fall back to the
[`esp32-serial-flash`](../../tree/esp32-serial-flash) branch.

---

## Download

| File | Contents |
|------|----------|
| `pmc8-esp32-ota-20260418-6523c90.zip` | Full distribution (~1 MB) |
| [`OTA_QUICK_START_V2.txt`](OTA_QUICK_START_V2.txt) | Read the manual here before you download |

Click the zip filename above → click **Download raw file** (the small
download arrow in GitHub's file view) to save it to your PC. The user
guide is the same file bundled inside the zip, posted here so you can
read it in your browser before committing to the procedure.

## What's in the zip

After extracting you'll have:

```
pmc8-esp32-ota-YYYYMMDD-<sha>\
    ota_update_v2.py                 <- the walkthrough script
    OTA_QUICK_START_V2.txt           <- written instructions
    MANIFEST.txt                     <- build provenance
    firmware\
        esp-at.bin                   <- ESP32 OTA firmware payload (~1.5 MB)
```

## Prerequisites

- Windows 10 or 11
- Python 3.x (the script will offer to `pip install` pyserial if missing)
- USB cable from PC to the PMC-Eight
- Either **direct access** to the PMC-8's own Wi-Fi network (AP mode) OR
  **a home Wi-Fi network** that both your PC and the PMC-8 can join

## Quick Start

1. Download the zip above and extract it somewhere easy like `C:\PMC8_OTA\`.
2. Open a Command Prompt in the extracted folder.
3. Run:
   ```
   python ota_update_v2.py
   ```
4. Follow the prompts. The script supports two modes:
   - **Direct (AP mode)** — your PC is connected to the PMC-8's own Wi-Fi
     network (`PMC8_xxxx`). Simplest; no home Wi-Fi needed.
   - **LAN mode** — your PC and the PMC-8 are both on your home Wi-Fi
     network. The script connects the ESP32 to your SSID for the
     duration of the update, then returns to AP mode on next power cycle.

The full step-by-step procedure, troubleshooting, and safety notes are in
`OTA_QUICK_START_V2.txt` inside the zip (also previewable above).

## Safety

- The OTA procedure is safe: if a transfer fails, the PMC-8 keeps its
  existing working firmware and you can just retry.
- The ESP32 has automatic rollback protection — if the new firmware fails
  to boot for any reason, it reverts to the previous version.
- Do not power off the mount or unplug the USB cable while the transfer
  is in progress.
