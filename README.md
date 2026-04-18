# PMC-Eight Propeller Firmware

Latest PMC-Eight Propeller firmware binaries for use with the UFCT
(Universal Firmware Configuration Tool).

## Current Version: 20A02.1.8.3

Two variants are provided. Both run on the same PMC-Eight hardware; the
difference is whether the firmware leaves the ESP32 Wi-Fi module enabled
at runtime:

| File | Behavior |
|------|----------|
| `20A02.1.8.3.bt.binary` | **Default.** Wi-Fi module active — needed for ExplorestarsLite, the HTTP bridge, and any wireless control. Use this unless you have a specific reason not to. |
| `20A02.1.8.3.no_wifi.binary` | Same firmware, but keeps the ESP32 Wi-Fi module disabled at runtime. Use this if you only control the mount over USB and want to (a) reduce the mount's power draw or (b) minimize RFI from the Wi-Fi radio for sensitive imaging setups. RN131-equipped units do not currently implement this feature. |

This version fully supports both the **Alpaca server** and the older
**ASCOM COM driver**. Users of either should load this firmware.

If you're not sure which variant to pick, use the `.bt` version.

## What's New Since 20A02.0

No intermediate 20A02.1.x versions were formally released; 20A02.1.8.3
is the first public release carrying all of the following improvements.

### Goto / slewing accuracy
- Major rework of RA cruise and ramp-down calculations so long slews
  now land on target consistently.
- Added a final "finishing move" in RA for sub-arc-second goto accuracy.
- ESV reply now includes slew status, so the Alpaca server can tell when
  a goto has actually completed.

### Pulse guide
- Pulse-guide timing is now performed by the PMC-8 itself. Time
  resolution is extended to 4 hex digits (1 ms each), and guide status
  is reported in the ESV command reply. The Alpaca server uses this
  today; the current COM driver does not, but a soon-to-be-released
  COM driver will.

### Motors
- Support for ASKO motors (direction corrected; top-end current 2000 mA).
- NEMA-17 motor torque optimization (1 step per pulse).

### Wireless and networking
- **Simultaneous UDP + TCP operation (ESP32).** Alpaca discovery (UDP)
  and command traffic (TCP) now work at the same time, unconditionally.
  Users no longer need to set a UDP/TCP flag in the PMC-8 configuration —
  the mount responds to either.
- **Multiple simultaneous TCP clients** are now supported (ESP32 only).
- ESSi (Wi-Fi info) no longer power-cycles the Wi-Fi module unless the
  channel or IP mode actually changed — faster reconnects.
- Home-network Wi-Fi server-connect fix: the mount now dynamically
  adjusts its Wi-Fi settings based on whether it's in PMC-8 AP mode or
  on a home network.
- Compatible with **ESP32 AT firmware version 4.2**, required for the
  latest ExplorestarsLite and HTTP-bridge features. See the
  [`esp32-ota`](../../tree/esp32-ota) and
  [`esp32-serial-flash`](../../tree/esp32-serial-flash) branches of this
  repo for tools to upgrade the ESP32 firmware.
- Improved ESP32 send reliability.

### Various bug fixes and functional improvements

## How to Update

1. Download the `.binary` file for your mount variant from this branch.
2. Open **UFCT** (Universal Firmware Configuration Tool) on your PC —
   typically installed at `C:\ES_PMC8_UTILITIES\`.
3. Select the correct COM port → click **Get Configuration**.
4. Go to the **Firmware Update** tab.
5. Browse to the downloaded `.binary` file → click **PROG**.
6. Wait for UFCT to report success and the mount to reboot.

## Compatibility

- iEXOS-100
- EXOS-2
- Losmandy ES G-11

## Related

- [`esp32-ota`](../../tree/esp32-ota) — OTA update for the ESP32 Wi-Fi module
- [`esp32-serial-flash`](../../tree/esp32-serial-flash) — serial-flash fallback for the ESP32
