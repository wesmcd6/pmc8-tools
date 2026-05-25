# Configure PMC8 for Home Network Connection

A Windows desktop utility that puts an **Explore Scientific&trade; PMC-Eight&trade;**
(iEXOS / EXOS) mount's **WiFi module onto your home network** — so the mount
joins your router and gets an IP on your LAN instead of running as its own
access point. Works across the PMC-Eight WiFi module families: **ESP32,
ESP8266, and RN-131.**

## Download

📦 **[Download from the v1.0 release](https://github.com/wesmcd6/pmc8-tools/releases/tag/home-network-config-v1.0)**
— on the release page, under **Assets**, click
**`Configure-PMC8-Home-Network-v1.0.exe`**.

It's a **single executable, no installer and no .NET to install** — the .NET
runtime is bundled. Download it and run it.

## What it does

- **Select the modem type** — ESP32, ESP8266, or RN-131 (whichever WiFi module
  your PMC-Eight has).
- **Pick the COM port** — the list of serial ports populates automatically.
- **Enter your network SSID and password**, then write them to the module so it
  joins your home WiFi on boot.
- **Fetch the assigned IP address** the router gave the mount, so you can point
  ExploreStars / Envision / ASCOM / planetarium software at it.
- **Saves your credentials** to a local file so you don't have to retype them
  next time.

All communication is over **USB serial** (connect the PMC-Eight to the PC with a
USB cable and use the mount's COM port).

## Requirements

- Windows 10 / 11 (64-bit). **No .NET install needed** — it's self-contained.
- A USB-to-serial driver matching your PMC-Eight's adapter (FTDI / CH340 / etc.).
- Your WiFi network name (SSID) and password.

## Usage

1. Connect the PMC-Eight to the PC by USB and power it on.
2. Launch the app. Pick your **modem type**, then select the mount's **COM port**
   from the list.
3. Type your **SSID** and **password**.
4. Click the configure button to write the credentials; the log shows progress
   and the module reconnects to your network.
5. Use the **get IP address** button to read back the address the router
   assigned — that's the address your mount-control software connects to.

If you pick the wrong COM port, the app reports a COM-port error after a few
seconds instead of hanging.

## Related tools

- **[PMC-Eight UFCT](https://github.com/wesmcd6/pmc8-tools/tree/pmc8-ufct)** —
  configuration / firmware tool that can also **reset an RN-131 back to factory
  defaults** (useful before re-running this tool on a misconfigured module).
- **[ExploreStars Envision](https://github.com/wesmcd6/pmc8-tools/releases/latest)**
  — the mount-control app that connects to the mount once it's on your network.

## License & trademarks

**Free to use.** The executable is provided free of charge for configuring
Explore Scientific PMC-Eight mounts; you may use it and share the unmodified
official release. The source code is not included and is not open source at
this time (the author may choose to open it in the future). See [`LICENSE`](LICENSE)
for full terms.

This is an independent utility **authored and owned by Wes McDonald**, not by
Explore Scientific, LLC. Explore Scientific&trade;, ExploreStars&trade;, and
PMC-Eight&trade; are trademarks of
[Explore Scientific, LLC](https://www.explorescientific.com), used here with
acknowledgement.

Copyright © 2023-2026 Wes McDonald. All rights reserved.
