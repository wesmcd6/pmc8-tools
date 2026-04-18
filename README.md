# PMC-Eight ESP32 Serial Flash

Fallback path for reflashing the ESP32 firmware on your PMC-Eight when **OTA
update is not possible** — for example, when the ESP32 has no firmware, has
corrupted firmware, or has firmware too old to support OTA.

**Try OTA first:** if OTA works, it's much simpler — no opening the enclosure,
no hex wrench, no jumper, no risk to the fragile Wi-Fi antenna cable.
See the [`esp32-ota`](../../tree/esp32-ota) branch.

If OTA isn't an option, this branch provides a self-contained zip that
walks you through the serial flash procedure.

---

## Download

| File | Contents |
|------|----------|
| `pmc8-esp32-serial-flash-20260418-8aaf87d.zip` | Full distribution (1.4 MB) |
| [`SERIAL_FLASH_USER_GUIDE.txt`](SERIAL_FLASH_USER_GUIDE.txt) | Read the manual here before you download |

Click the zip filename above → click **Download raw file** (the small download
arrow in GitHub's file view) to save it to your PC. The user guide is the
same file bundled inside the zip, posted here so you can read it in your
browser before committing to the procedure.

## What's in the zip

After extracting you'll have:

```
pmc8-esp32-serial-flash-YYYYMMDD-<sha>\
    serial_flash.py                  <- the walkthrough script
    SERIAL_FLASH_USER_GUIDE.txt      <- written instructions
    MANIFEST.txt                     <- build provenance
    firmware\
        factory_WROOM-32.bin         <- 4 MB ESP32 flash image
        ESPLoad1.binary              <- Propeller transparent UART bridge
        pmc8_normal_firmware.binary  <- normal PMC8 Propeller firmware
    tools\
        proploader.exe               <- David Betz's P1 loader (MIT)
        proploader-LICENSE.txt
```

## Prerequisites

- Windows 10 or 11
- Python 3.x (the script will offer to `pip install` pyserial and esptool if
  they're missing)
- USB cable from PC to the PMC-Eight
- For the iEXOS-100: a 5/64" or 2 mm hex wrench (four bolts on the circuit
  board enclosure lid) and a small jumper / shorting block for the ESP32
  BOOT_OPT pins

## Quick Start

1. Download the zip above and extract it somewhere easy like `C:\PMC8_Flash\`.
2. Open a Command Prompt in the extracted folder.
3. Run:
   ```
   python serial_flash.py
   ```
4. Follow the prompts. The script:
   - Probes whether OTA can be used instead (and points you at the OTA
     branch if so)
   - Checks the Propeller firmware version and offers to update it if it's
     too old to support pass-through (< 20A02.0)
   - Tells you exactly when to install the BOOT_OPT jumper and when to
     remove it
   - Automatically handles the three binary loads (ESPLoader → ESP32
     firmware → normal Propeller firmware) via proploader and esptool
   - Verifies the update by reading the new ESP32 firmware version via
     AT+GMR and comparing to the binary's embedded version

The full step-by-step procedure, troubleshooting, and safety notes are in
`SERIAL_FLASH_USER_GUIDE.txt` inside the zip.

## Safety

- The mount can stay powered and USB-connected throughout; you only need to
  open the enclosure to install/remove the BOOT_OPT jumper.
- If you're uncomfortable opening the enclosure or handling the fragile
  Wi-Fi antenna cable inside, stop and contact Explore Scientific support.
- A failed flash can always be retried — the PMC-Eight keeps its existing
  working firmware until a new binary is successfully written.
