# PMC-Eight Universal Firmware Configuration Tool (UFCT)

A Windows desktop utility for inspecting and configuring **PMC-Eight&trade;**
telescope mount controllers from Explore Scientific&trade;. Reads and writes the
controller's internal configuration parameters, sends raw protocol commands for
diagnostics, performs firmware updates, and (for RN-131-based modules) restores
the WiFi adapter to factory defaults.

## Download

📦 **[Download `PMC-Eight-UFCT-2.0.exe`](PMC-Eight-UFCT-2.0.exe)** — on the file
page that opens, click the **Download** button (top right).

It's a **single executable, no installer**. Download it and run it.

## What it does

- **Get / Set Configuration** — reads all `ESGi!` parameters from the mount
  (baud rate, WiFi enable, channel, motor counts, max rate, etc.), shows them
  in editable form, and writes them back as a single `ESSi…!` packet.
- **Send raw command** — type any `ES…!` protocol command and send it directly
  to the mount; the reply shows in the log.
- **Reboot Show Splash** — issues the reboot command (serial stays connected and
  drains the splash; WiFi disconnects cleanly so you can re-verify the IP).
- **Firmware Update** — picks a `.binary`/`.eeprom` firmware file off disk and
  writes it to the mount's EEPROM over serial using a **built-in Propeller P1
  loader — no external tooling** (Propellent / Propeller IDE) required.
- **Restore RN-131** — wipes a misconfigured RN-131 WiFi module back to factory
  defaults so it can re-join a network. (RN-131 specific.)
- **Motion Test** — basic move-the-mount sanity checks.

All actions run over **USB serial** (any PMC-Eight controller with a COM port)
or **WiFi/TCP** (any PMC-Eight WiFi module exposing the protocol on a socket).

## Supported hardware

- PMC-Eight controllers (Model 2A-01 and family) over USB serial.
- All PMC-Eight WiFi modules across the product history — **RN-131, ESP8266,
  ESP32** — over raw TCP on port 54372. No module-type selection needed; the
  tool sanitises module-specific quirks (e.g. RN-131's unsolicited `*HELLO*`
  greeting) at the response layer so one code path works for all of them.

## Requirements

- Windows 10 / 11
- .NET Framework 4.8 runtime (ships with current Windows)
- A USB-to-serial driver matching your PMC-Eight's adapter (FTDI / CH340 / etc.)
  — only needed for the serial path
- For WiFi: the mount and the PC on the same LAN

## Usage

### Serial
1. Plug PMC-Eight into a USB port.
2. Launch UFCT. The COM port list populates automatically; pick the right one.
3. Click **GET Current Configuration**. The log shows the `ESGi!` reply, the
   firmware version (`ESGv!`), then `CURRENT CONFIGURATION RETRIEVED!`, and the
   form fields fill in.
4. Edit values, click **SET New Configuration** to push them back (the
   controller reboots on `ESSi!`).
5. For ad-hoc diagnostics: type a command (e.g. `ESGv!`) and click **SEND COMMAND**.

### WiFi
1. Get the mount's WiFi IP (provision it ahead of time — for RN-131 via the
   legacy *Configure PMC-8 For Home Network* app or this tool's **Restore
   RN131**; for ESP modules, the firmware's own AP/setup flow).
2. Type the IP into the **Mount IP** field next to **Connect WiFi**.
3. Click **Connect WiFi** — connects in under 3 seconds or fails fast.
4. The Firmware Update tab greys out while WiFi-connected (firmware updates are
   serial-only).
5. All Get / Set / Send actions route over TCP automatically.
6. Click **Disconnect WiFi** when done.

## Version

**v2.0** (May 2026) — full refactor on .NET Framework 4.8 with typed
protocol/transport/config layers and WiFi connectivity working end-to-end
across all PMC-Eight WiFi modules (RN-131 / ESP8266 / ESP32), single
Connect/Disconnect with Mount IP entry, fast-fail WiFi connect, and a built-in
Propeller P1 firmware loader (ported from dbetz's MIT `p1load`) so firmware
updates run directly over serial with no Propellent.exe / Propeller IDE.

## License

Copyright © 2022–2026 Explore Scientific, LLC. All rights reserved.

This is proprietary tooling for Explore Scientific PMC-Eight controllers.
Distribution is limited to authorized collaborators at Explore Scientific's
discretion. See `LICENSE` for the full terms.

Portions are derived from third-party open-source code (the Propeller P1 boot
protocol in the firmware loader, ported from dbetz's MIT-licensed `p1load`).
Those portions remain under their original licenses; full notices are in
`THIRD_PARTY_NOTICES.md`.

## Authors

- Jerry Hubbell (`ExploreScientific`) — original author of the v1.x tool
- Wes McDonald (`wesmcd6`) — v2.x refactor lead
- Copyright held by Explore Scientific, LLC

## Third-party credits

- `p1load` by **dbetz** (<https://github.com/dbetz/p1load>, MIT) — source for
  the Propeller P1 boot protocol ported into the firmware loader.
- The LFSR handshake and long-encoding constants trace to Chip Gracey's PNut /
  Propeller Tool boot loader.

See `THIRD_PARTY_NOTICES.md` for full license text.
