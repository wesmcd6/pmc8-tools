# PMC-Eight ESP32 OTA Update

Update your PMC-Eight's ESP32 firmware **over-the-air** — no opening the
enclosure, no hex wrench, no jumper, no risk to the fragile Wi-Fi antenna
cable. This is the **simplest** way to update the ESP32 firmware.

**This release: ES4.2.29 (July 2026).** See *What's new* below.

If OTA isn't possible (ESP32 has no firmware, has corrupted firmware, or
has firmware too old to support OTA), fall back to the
[`esp32-serial-flash`](../../tree/esp32-serial-flash) branch.

---

## What's new in this update

This release lets the Wi-Fi adapter **serve Bluetooth and Wi-Fi at the same
time** and talk to the mount with **much less overhead** — a faster, leaner,
more reliable conversation.

- **Bluetooth *and* Wi-Fi, together.** You can now drive the mount from a
  Bluetooth app and a Wi-Fi / PWA app **at the same time** — the adapter keeps
  both conversations straight instead of making you pick one.
- **You'll see it today with ExploreStars Envision**, which already uses the
  upgraded adapter: more responsive, smoother control and live position
  display, and a steadier connection that holds up better when other tools
  are also in use.
- **Cleaner, more reliable connections.** This build irons out the mode
  transitions so connections come and go without hiccups.
- **Your other apps keep working — unchanged.** This update won't break
  anything you already use.
- **The best is still ahead.** Further Envision updates will keep improving
  performance by using this firmware to its fullest, and other Explore
  Scientific apps gain the same as they adopt it. Updating the adapter now
  means you're ready — each improvement arrives the moment the apps ship it,
  with no second firmware update needed.

It updates **only the Wi-Fi adapter** — it does not change your mount's
motor/control firmware or how the mount itself behaves.

---

## Download

| File | Contents |
|------|----------|
| `pmc8-esp32-ota-20260707-7b39e9b.zip` | ✅ **NEW — download this** · ES4.2.29 firmware (~1 MB) |
| `pmc8-esp32-ota-20260627-483fd19.zip` | Older — ES4.2.27 firmware (previous version, for rollback) |
| [`OTA_QUICK_START_V2.txt`](OTA_QUICK_START_V2.txt) | Read the manual here before you download |

Most people want the one marked **NEW** (top row). Click a zip filename above → click
**Download raw file** (the small download arrow in GitHub's file view) to
save it to your PC. The user guide is the same file bundled inside the zip,
posted here so you can read it in your browser before committing to the
procedure.

## What's in the zip

After extracting you'll have:

```
pmc8-esp32-ota-YYYYMMDD-<sha>\
    ota_update_v2.py                 <- the walkthrough script
    OTA_QUICK_START_V2.txt           <- written instructions
    MANIFEST.txt                     <- build provenance
    esp-at.bin                       <- ESP32 OTA firmware payload (~1.3 MB)
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
