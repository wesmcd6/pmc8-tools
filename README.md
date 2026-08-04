# PMC-Eight ESP32 Serial Flash

Rescue path for reflashing the ESP32 Wi-Fi module on your PMC-Eight when **OTA
update is not possible** — when the ESP32 has no firmware, has corrupted
firmware, or has firmware too old to support OTA.

**Try OTA first.** If your mount still talks over Wi-Fi, the
[`esp32-ota`](../../tree/esp32-ota) updater is far simpler — no opening the
enclosure, no hex wrench, no jumper, no risk to the fragile Wi-Fi antenna cable.
This tool checks for you and will tell you to go and use it.

---

## Download

**⬇ [Download the latest release](../../releases/tag/esp32-serial-flash-v1.0)** —
`pmc8-esp32-serial-flash-v1.0-ES4.2.3.zip`

Downloads moved to Releases in v1.0. Previous versions were files committed to
this branch; the release page carries the zip, a `.sha256` to check it against,
and notes on what changed.

📖 **[Read the user guide first](SERIAL_FLASH_USER_GUIDE.txt)** — the same file as
the one inside the zip, posted here so you can read it in your browser before
committing to the procedure. **Please do read it.** This one involves a
screwdriver.

## Runs on Windows, macOS and Linux / Raspberry Pi

| | how to start it |
|---|---|
| Windows | `python serial_flash.py` |
| macOS | double-click `start_flash.command` |
| Linux / Raspberry Pi | `./start_flash.sh` |

Tested with a full flash on all three.

## What's in the zip

```
serial_flash.py                  <- the walkthrough script
start_flash.sh                   <- launcher: Linux / Raspberry Pi
start_flash.command              <- launcher: macOS (double-click)
p1_loader.py                     <- built-in Propeller loader (MIT)
SERIAL_FLASH_USER_GUIDE.txt      <- written instructions
THIRD_PARTY_NOTICES.md           <- licences for bundled components
MANIFEST.txt                     <- build provenance
firmware/
    factory_WROOM-32.bin         <- 4 MB ESP32 flash image
    ESPLoad1.binary              <- Propeller transparent UART bridge
    pmc8_normal_firmware.binary  <- normal PMC-Eight Propeller firmware
```

Everything needed is in there. Nothing else to download, on any platform.

## Prerequisites

- Windows 10/11, macOS, or Linux (including Raspberry Pi OS)
- Python 3 — on Windows install it with **"Add python.exe to PATH"** checked;
  macOS and Linux normally have it already. The macOS and Linux launchers check
  for it and for the two Python packages needed (`pyserial`, `esptool`), and
  install them if missing.
- USB cable from the computer to the PMC-Eight
- For the iEXOS-100: a 5/64" or 2 mm hex wrench (four bolts on the circuit board
  enclosure lid) and a small jumper / shorting block for the ESP32 BOOT_OPT pins

## Quick start

1. Download the zip from the release above and extract it, keeping the files
   together.
2. Start it using the table above for your system.
3. Follow the prompts. The script:
   - Checks whether OTA can be used instead, and sends you there if it can
   - Checks your Propeller firmware version, and offers to update it if it is
     too old to support the pass-through bridge (< 20A02.0)
   - Tells you exactly when to fit the BOOT_OPT jumper, when to switch the mount
     off and on, and when to remove the jumper again
   - Handles all three binary loads itself
   - **Checks the Wi-Fi module is really ready before writing anything** — if it
     is not, it stops without touching your firmware and tells you what to look
     at
   - Verifies the result afterwards, and puts your Propeller firmware back if
     anything goes wrong partway through

The window stays open until you press Enter, so you can always read what
happened.

Full step-by-step procedure, troubleshooting and safety notes are in the user
guide.

## ⚠️ After it works, you are not finished

The firmware this installs (**ES4.2.3**) is **deliberately an older version**. Its
job is to get a dead Wi-Fi module booting again reliably — not to be the version
you stay on. Some features, including Envision mode, are not in it at all.

Once your mount is working again, run the
[OTA updater](../../tree/esp32-ota) to bring it up to current. A few minutes over
Wi-Fi, no tools. The script reminds you when it finishes.

## Safety

- The USB cable stays connected throughout. The mount only has to be switched off
  for one deliberate power cycle partway through, which the script asks for. The
  BOOT_OPT jumper can be fitted and removed on a live board — but if you would
  rather not work on live electronics, you can power off for those steps too. The
  script waits for you at each one.
- **Remove the BOOT_OPT jumper when you are done.** Left in place it makes the
  ESP32 restart into programming mode every time you power on, so the mount has
  no Wi-Fi and appears dead when nothing is wrong with it.
- If you are uncomfortable opening the enclosure or handling the fragile Wi-Fi
  antenna cable inside, stop and contact Explore Scientific support.
- A failed flash can be retried. The mount keeps its existing working firmware
  until a new image is successfully written.
