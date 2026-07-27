# PMC-Eight Propeller Firmware

Latest PMC-Eight Propeller firmware binaries, for use with the **PMC8 Dashboard** or
the UFCT (Universal Firmware Configuration Tool).

## Current Version: 20A02.2.0.0

| File | Behavior |
|------|----------|
| `20A02.2.0.0.bt.binary` | **Current release.** Wi-Fi module active — needed for ExplorestarsLite, the HTTP bridge, and any wireless control. |
| `20A02.1.8.3.no_wifi.binary` | Previous release, Wi-Fi module kept disabled at runtime. Use this only if you control the mount solely over USB and want to reduce power draw or minimize RFI for sensitive imaging. A no-Wi-Fi build of 20A02.2.0.0 has not been produced — ask if you need one. RN131-equipped units do not implement this feature. |

Reports as `ES20A02.2.0.0.bt Release 2026.07.27`.

Fully supports both the **Alpaca server** and the older **ASCOM COM driver**.

---

## What's New in 20A02.2.0.0

### Your mount remembers your network — and serves two at once

This is the big one.

Program your PMC-Eight onto your home Wi-Fi and **it stays there**, across power
cycles, without re-entering anything. At the same time the mount keeps serving its own
`47.1` network, so both connections are live simultaneously.

What that means in practice:

- **Set it once.** No reconfiguring the mount's network settings every session.
- **Stay on your home network.** Your phone, tablet or PC can talk to the mount
  without dropping off Wi-Fi and losing internet, sky catalogs, or anything else it
  was using.
- **Keep the direct connection as a fallback.** `47.1` is still there whenever you
  want it — in the field, or if the home network is unavailable. You no longer have to
  choose one or the other.

Applies to ESP32 equipped units.

**ESP8266 owners:** this needs newer module firmware than is currently released, so it
does not reach your unit yet. That new 8266 firmware is written and in beta test now.
It brings both networks live at once, the home network remembered across power cycles,
and fast mode below. It will follow shortly.

### Fast mode — quicker and steadier communication

If you update your ESP32 module to the latest firmware, this release can talk to it a
new way. Look for **Envision mode** in Envision, or **Fast mode** in the PMC8
Dashboard.

Normally every message the mount sends is wrapped in a short back-and-forth with the
Wi-Fi module: a command announcing the message, a wait for the module to say it is
ready, the data itself, then a wait for confirmation. That happens for *every* reply —
and software like the Alpaca/ASCOM driver asks the mount for its status constantly.

In fast mode that wrapper goes away and the data passes straight through. Two things
follow from that:

- **Lower latency.** Status and position updates arrive with less delay, so slewing
  and real-time feedback feel more immediate.
- **Fewer communication faults.** Most of the Wi-Fi trouble chased over the past year
  traced back to that handshake going wrong under load — the module busy at the wrong
  moment, a confirmation arriving late or not at all. Remove the handshake and that
  whole class of problem goes with it.

Requires an ESP32 running current module firmware. If you would rather not enable it,
everything behaves exactly as before. See the
[`esp32-ota`](../../tree/esp32-ota) and
[`esp32-serial-flash`](../../tree/esp32-serial-flash) branches for tools to update the
module.

### Works with newer Wi-Fi modules

The firmware now correctly recognizes newer ESP32 (4.x) module firmware. If you have a
module that shipped with newer firmware — or you update one — it will now initialize
properly and keep Bluetooth available. Older modules continue to work exactly as
before.

### Reliability fixes

- **More robust Wi-Fi command handling.** A truncated or garbled incoming packet
  header can no longer be mistaken for a valid command. On a marginal connection this
  means fewer odd behaviors and dropped commands.
- **Settings storage fix.** A routine that restores saved settings could read past the
  end of its buffer. Corrected.
- **Faster recovery from an incomplete network send**, so the mount gets back to
  normal operation sooner when a packet doesn't make it.

### Under the hood

Various refactors to free up code space for future features. No change in behavior.

---

## How to Update

**PMC8 Dashboard v0.2.5 is recommended.** Because this release lets the mount hold two
addresses at once, the tool you use needs to understand that — the Dashboard reports
both correctly, and the UFCT may not. The Dashboard is also cross-platform.

Download it here:
[PMC8 Dashboard v0.2.5](https://github.com/wesmcd6/pmc8-tools/releases/tag/pmc8-dashboard-v0.2.5)

### Using the UFCT instead

1. Download the `.binary` file from this branch.
2. Open **UFCT** on your PC — typically installed at `C:\ES_PMC8_UTILITIES\`.
3. Select the correct COM port → click **Get Configuration**.
4. Go to the **Firmware Update** tab.
5. Browse to the downloaded `.binary` file → click **PROG**.
6. Wait for UFCT to report success and the mount to reboot.

## Compatibility

- iEXOS-100
- EXOS-2
- Losmandy ES G-11

Works with all the PMC-Eight ecosystem software you are accustomed to.

---

## Previously, in 20A02.1.8.3

No intermediate 20A02.1.x versions were formally released; 20A02.1.8.3 carried all of
the following.

### Goto / slewing accuracy
- Major rework of RA cruise and ramp-down calculations so long slews now land on
  target consistently.
- Added a final "finishing move" in RA for sub-arc-second goto accuracy.
- ESV reply now includes slew status, so the Alpaca server can tell when a goto has
  actually completed.

### Pulse guide
- Pulse-guide timing is now performed by the PMC-8 itself. Time resolution is extended
  to 4 hex digits (1 ms each), and guide status is reported in the ESV command reply.

### Motors
- Support for ASKO motors (direction corrected; top-end current 2000 mA).
- NEMA-17 motor torque optimization (1 step per pulse).

### Wireless and networking
- **Simultaneous UDP + TCP operation (ESP32).** Alpaca discovery (UDP) and command
  traffic (TCP) now work at the same time, unconditionally.
- **Multiple simultaneous TCP clients** are now supported (ESP32 only).
- ESSi (Wi-Fi info) no longer power-cycles the Wi-Fi module unless the channel or IP
  mode actually changed — faster reconnects.
- Home-network Wi-Fi server-connect fix.
- Compatible with **ESP32 AT firmware version 4.2**.
- Improved ESP32 send reliability.

## Related

- [`esp32-ota`](../../tree/esp32-ota) — OTA update for the ESP32 Wi-Fi module
- [`esp32-serial-flash`](../../tree/esp32-serial-flash) — serial-flash fallback for the ESP32
