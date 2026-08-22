# PMC-Eight ESP8266 Serial Flash

For PMC-Eight mounts with the **ESP8266** Wi-Fi module.

The firmware that shipped on those mounts **predates over-the-air updating** —
there is no way to update them wirelessly, because the firmware on them has no
update command to receive. If you have been locked out of features that arrived
later, that is why.

This tool is the way out. It writes new firmware over the USB cable, and the
firmware it writes **does** support over-the-air updates.

```
BEFORE   no way to update at all
NOW      run this once, with a jumper and a screwdriver
AFTER    every future update is over Wi-Fi, enclosure closed
```

You should not need it a second time. Keep it anyway — it is also the rescue
path if a module is ever left without working firmware.

---

## Download

**⬇ [Download the latest release](../../releases/tag/esp8266-serial-flash-v1.0)** —
`pmc8-esp8266-serial-flash-v1.0-2.2.40-env.zip`

The release page carries the zip and a `.sha256` to check it against.

📖 **[Read the user guide first](SERIAL_FLASH_USER_GUIDE.txt)** — the same file as
the one inside the zip, posted here so you can read it in your browser before
committing to the procedure. **Please do read it.** This one involves a
screwdriver.

## Do you have an ESP8266 or an ESP32?

This installs ESP8266 firmware and will not work on an ESP32. You have to open
the enclosure anyway, so the check is by eye — and the script asks you to
confirm before it writes anything:

- **ESP32** — an antenna is attached to the **lid**
- **ESP8266** — no lid antenna; a **blue extension from the side of the silver
  module**, above the USB connector

⚠️ **If you are not sure, open the lid carefully.** On ESP32 mounts the antenna
is attached to it on a short, fragile cable.

For ESP32 mounts, use [`esp32-ota`](../../tree/esp32-ota) if Wi-Fi still works,
or [`esp32-serial-flash`](../../tree/esp32-serial-flash) if it does not.

## Runs on Windows, macOS and Linux / Raspberry Pi

| | how to start it |
|---|---|
| Windows | `python serial_flash.py` |
| macOS | double-click `start_flash.command` |
| Linux / Raspberry Pi | `./start_flash.sh` |

Tested with a full flash of a real mount on **all four from the one download**.
Nothing is rebuilt per platform.

On macOS and Linux the launcher installs the two Python packages it needs the
first time you run it. Just answer yes.

## What you need

- The mount, powered, connected by USB
- A small Phillips screwdriver
- **One jumper** — the small shorting block from an old PC hard drive is exactly
  the right thing
- Python 3

About twenty minutes.

## After it works

Your module supports over-the-air updates from then on. The next firmware update
will not need this tool, the enclosure, the jumper or the screwdriver.
