# PMC-Eight Propeller Firmware

Latest PMC-Eight Propeller firmware binaries for use with the UFCT
(Universal Firmware Configuration Tool).

## Current Version: 20A02.1.8.3

Two variants are provided. All PMC-Eight units have the ESP32 Wi-Fi
module; both variants run on the same hardware. The difference is
whether the firmware leaves Wi-Fi enabled at runtime:

| File | Behavior |
|------|----------|
| `20A02.1.8.3.bt.binary` | **Default.** Wi-Fi + Bluetooth Classic active — needed for ExplorestarsLite, the HTTP bridge, and any wireless control. Use this unless you have a specific reason not to. |
| `20A02.1.8.3.no_wifi.binary` | Same firmware, but keeps the ESP32 Wi-Fi turned OFF. Use this if you only drive the mount over a wired serial / USB connection and want to (a) reduce the mount's power draw or (b) reduce RFI that can affect sensitive imaging setups. |

If you're not sure which one you want, use the `.bt` version.

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
