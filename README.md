# PMC-Eight ESP32 OTA Update

Update your PMC-Eight's ESP32 firmware **over-the-air** — no opening the
enclosure, no hex wrench, no jumper, no risk to the fragile Wi-Fi antenna
cable. This is the **simplest** way to update the ESP32 firmware.

**This release: ES4.2.30 firmware, updater v2.4.** See *What's new* below.

If OTA isn't possible (ESP32 has no firmware, has corrupted firmware, or
has firmware too old to support OTA), fall back to the
[`esp32-serial-flash`](../../tree/esp32-serial-flash) branch. The updater
tells you if this applies to you, before it changes anything.

---

## What's new in the firmware

This release lets the Wi-Fi adapter talk to the mount with **much less
overhead** — a faster, leaner conversation — and makes switching that faster
mode on and off dependable.

- **Less back-and-forth, quicker responses.** In the adapter's fast
  (Envision) mode, data passes straight through instead of being wrapped in a
  handshake for every single reply. Lower latency, and fewer of the
  communication faults that handshake caused under load.
- **You'll see it today with ExploreStars Envision**, which already uses the
  upgraded adapter: more responsive, smoother control and live position
  display, and a steadier connection.
- **Bluetooth and Wi-Fi together, in fast mode.** Earlier builds gave up
  Bluetooth when the adapter switched over. Now it keeps both — a Bluetooth
  app and a Wi-Fi / PWA app can drive the mount at once, because in fast mode
  every client is funnelled through a single queue and they can't talk over
  each other. In testing this has held up well. Do bear in mind the adapter
  runs both radios from one antenna, so if you lean on both connections hard
  at the same time, expect throughput to give a little.
- **Leaving fast mode is reliable.** The signal that brings the adapter back
  is now recognised however it arrives, so switching off no longer risks
  leaving the adapter unresponsive to further commands. Pair this with mount
  firmware `20A02.2.0.1` or later, which sends that signal correctly.
- **Your other apps keep working — unchanged.** This update won't break
  anything you already use.
- **The best is still ahead.** Further Envision updates will keep improving
  performance by using this firmware to its fullest, and other Explore
  Scientific apps gain the same as they adopt it. Updating the adapter now
  means you're ready — each improvement arrives the moment the apps ship it,
  with no second firmware update needed.

It updates **only the Wi-Fi adapter** — it does not change your mount's
motor/control firmware or how the mount itself behaves.

## What's new in the updater (v2.4)

- **It tells you straight away if your module is too old to update.** Some
  early Wi-Fi modules don't support over-the-air updates at all and need the
  serial-flash tool instead. The updater now checks for that in the first few
  seconds — **before** it asks for a firmware file, before it asks for your
  Wi-Fi password, and before it touches the module's network settings. It used
  to find out only near the end, after all of that.
- **Clearer Linux serial-port advice.** After adding yourself to the `dialout`
  group you must **reboot** — logging out and back in is not enough on current
  Ubuntu, which left people stuck with a port that would not open.

## Earlier, in v2.3

- **Works on macOS**, which it previously did not — and there's nothing to
  type: double-click `start_ota.command`.
- **Launcher for Linux and Raspberry Pi too** — `./start_ota.sh`. (The
  `.sh` does the work; `start_ota.command` is a small wrapper that runs it,
  named that way because the macOS Finder needs a `.command` file to
  double-click a script. Linux goes by the executable bit rather than the
  extension, so on a Pi desktop double-clicking either file generally works
  as well.)
- **No serial port to find.** The updater locates the mount by itself, on
  every platform.
- **It refuses to install the wrong firmware** (see *ESP32 modules only*).
- **Envision mode handled automatically** — the ESP32 ignores update commands
  while it's on, which used to cause a confusing mid-run failure.

---

## Download

### 👉 [**Get the latest release**](../../releases/tag/esp32-ota-v2.4)

Download **`pmc8-esp32-ota-v2.4-ES4.2.30.zip`** from that page.

Older versions stay available on the [releases page](../../releases) if you
ever need to roll back.

You can read the user guide in your browser before downloading:
[**OTA_QUICK_START_V2.txt**](OTA_QUICK_START_V2.txt) — it's the same file
that's bundled inside the zip.

## ESP32 modules only

This package updates **ESP32** Wi-Fi modules. Some PMC-Eights have an
**ESP8266** instead, which needs a different firmware package — those are
different chips, not different versions.

You don't have to know which you have. The updater checks your mount against
the firmware and **stops safely, changing nothing**, if they don't match.

## What's in the zip

After extracting you'll have:

```
pmc8-esp32-ota-v2.4-ES4.2.30\
    ota_update_v2.py                 <- the walkthrough script
    start_ota.sh                     <- Linux / Raspberry Pi: run this
    start_ota.command          <- macOS: double-click this
    OTA_QUICK_START_V2.txt           <- written instructions
    MANIFEST.txt                     <- build provenance
    esp-at.bin                       <- ESP32 OTA firmware payload (~1.3 MB)
```

## Prerequisites

- **Any desktop OS:** Windows 10/11, **macOS**, or **Linux — including Raspberry Pi.**
  The tool is pure Python + `pyserial` with no OS-specific dependencies.
- Python 3.x (the updater installs `pyserial` for you if it's missing)
- USB cable from your computer to the PMC-Eight
- Either **direct access** to the PMC-8's own Wi-Fi network (AP mode) OR
  **a home Wi-Fi network** that both your computer and the PMC-8 can join

## Quick Start

1. Download the zip and extract it somewhere easy (`C:\PMC8_OTA\` on
   Windows; `~/pmc8-ota/` on macOS / Linux / Raspberry Pi).
2. Connect the USB cable and power on the mount.
3. Run it. **You do not need to find or type a serial port** — the updater
   locates the mount itself:

   | | |
   |---|---|
   | **macOS** | double-click `start_ota.command` |
   | **Linux / Raspberry Pi** | `./start_ota.sh` |
   | **Windows** | `python ota_update_v2.py` |

4. Follow the prompts. The updater supports two modes:
   - **Direct (AP mode)** — your computer is connected to the PMC-8's own Wi-Fi
     network (`PMC8_xxxx`). Simplest; no home Wi-Fi needed.
   - **LAN mode** — your computer and the PMC-8 are both on your home Wi-Fi
     network. The updater connects the ESP32 to your SSID for the
     duration of the update, then returns to AP mode on next power cycle.

### macOS — first launch only

macOS blocks the launcher once, because it isn't signed by a paid Apple
developer account. Dismiss the message, then **System Settings ▸ Privacy &
Security**, scroll to Security, click **Open Anyway**, then double-click again
and choose **Open**. Once only.

### Naming the serial port yourself (rarely needed)

Only if more than one USB-serial adapter is attached and the updater picks the
wrong one:

| OS | Typical port | How to list them |
|----|--------------|------------------|
| Windows | `COM3`, `COM11`, … | Device Manager → *Ports (COM & LPT)* |
| Linux / Raspberry Pi | `/dev/ttyUSB0` or `/dev/ttyACM0` | `ls /dev/ttyUSB* /dev/ttyACM*` |
| macOS | `/dev/cu.usbserial-XXXX` | `ls /dev/cu.*` |

On macOS use the `/dev/cu.*` name, never its `/dev/tty.*` twin.

### Platform notes

- **Linux / Raspberry Pi:** grant serial access once — `sudo usermod -aG dialout $USER`,
  then **reboot**. Logging out and back in is *not* enough on current Ubuntu/GNOME:
  the systemd user session survives a logout and keeps your old group membership, so
  the port still refuses to open. (`newgrp dialout` gets it in the current terminal
  only; `sudo` also works.) If you run a firewall (`ufw`), allow the update server's
  port: `sudo ufw allow 8000/tcp`. (Stock Raspberry Pi OS has no blocking firewall,
  so usually nothing to do.)
- **macOS:** the first run may pop *"Do you want the application 'Python' to accept
  incoming network connections?"* — click **Allow** (the ESP has to reach the tool's
  built-in web server to pull the firmware).
- **Windows:** the tool adds its own temporary firewall rule automatically; on
  macOS / Linux there's no rule to add and that step is skipped.

### Two pauses that look like a freeze — both normal

- **"Checking the mount is responding…"** — on macOS and Linux, opening the USB
  port makes the mount restart. The updater waits it out (about 25 seconds) with
  a countdown. Windows users won't see this at all.
- **"Waiting 15s for the ESP32 modem to reset"** — after Envision mode is switched
  off. The mount itself does not restart here, only the Wi-Fi module.

> Envision mode is left **off** after the update. Turn it back on in
> ExploreStars Envision ▸ Setup ▸ Envision Mode.

The full step-by-step procedure, troubleshooting, and safety notes are in
`OTA_QUICK_START_V2.txt` inside the zip (also previewable above).

## Safety

- The OTA procedure is safe: if a transfer fails, the PMC-8 keeps its
  existing working firmware and you can just retry.
- The ESP32 has automatic rollback protection — if the new firmware fails
  to boot for any reason, it reverts to the previous version.
- Do not power off the mount or unplug the USB cable while the transfer
  is in progress.
