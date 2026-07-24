# PMC8 Dashboard v0.2.5

PMC8 Dashboard v0.2.5 is a Python/PyQt6 desktop utility for configuring and testing an Explore Scientific PMC-Eight controller.

## Downloads

Grab the ZIP for your platform (PMC8 Dashboard v0.2.5):

- [**Windows**](https://github.com/wesmcd6/pmc8-tools/releases/download/pmc8-dashboard-v0.2.5/PMC8_Dashboard_Windows.zip) — `PMC8_Dashboard_Windows.zip`
- [**macOS**](https://github.com/wesmcd6/pmc8-tools/releases/download/pmc8-dashboard-v0.2.5/PMC8_Dashboard_macOS.zip) — `PMC8_Dashboard_macOS.zip`
- [**Linux / Raspberry Pi (64-bit)**](https://github.com/wesmcd6/pmc8-tools/releases/download/pmc8-dashboard-v0.2.5/PMC8_Dashboard_Linux.zip) — `PMC8_Dashboard_Linux.zip`

For the newest version, see the [PMC8 Dashboard releases](https://github.com/wesmcd6/pmc8-tools/releases?q=pmc8-dashboard) on the tools page. Extract the ZIP and follow the matching setup section below.

## What's new in v0.2.5

- **Get WiFi Address shows both addresses.** For ESP32/ESP8266 modules it now reports the **home-network address and the access-point address (192.168.47.1)** together when both are up, instead of just one — and pre-fills the WiFi connect field with the home address.
- **The Network tab picks your module for you.** Get Configuration detects the WiFi module type and sets the Network tab's module dropdown to match, so you don't have to. This also fixes a case where an ESP32 could be mislabeled "RN-131, Fast Server not supported."
- **Smoother on Linux / Raspberry Pi.** Connecting over serial resets the mount on Linux (a kernel quirk of opening the port); the app now waits for it to come back and fills in the configuration automatically, so a connect just works instead of looking dead.
- **Steadier WiFi command handling.** A command the mount silently ignores no longer looks like a dropped connection, and a command typed directly into the console (`ESGi!`, `ESGe!`) updates the on-screen fields, not just the log.
- **More compact window.** The Configurator tab is tighter — the response log is visible without scrolling, and the window is narrower.

### Earlier: v0.2.4

- **RN131 home-network setup now handles passwords (and SSIDs) with spaces.** A space used to truncate the value at the first word, so the RN131 stored the wrong key and failed to authenticate (`AUTH-ERR`), looping without joining. Spaces are now sent correctly; if you saw this before, update and try again.
- **RN131 WiFi address reads faster**, and the Network tab no longer sends a Fast Server query to RN131 modules (they don't have it) — so setup is quicker and the log is cleaner.
- **Clearer help when an RN131 won't join.** If a saved password is wrong the module gets stuck retrying, which blocks reconfiguring; the log now says so and points you to Restore to Default first. It also notes that RN131 modules are 2.4 GHz WPA/WPA2 only and can't join WPA3-only or PMF-required networks common on newer routers.

> **RN131 (EXOS2) and modern routers:** RN131 WiFi modules are older 2.4 GHz radios that speak WPA/WPA2 only. They cannot join a network that is WPA3-only, runs WPA2/WPA3 "transition" mode, or requires Protected Management Frames (PMF) — increasingly common on newer WiFi 6 routers. If an RN131 can see the network but the log shows an authentication error (`AUTH-ERR`) and it keeps retrying, point the mount at a **2.4 GHz WPA2** network (a guest or IoT SSID is ideal). ESP32 and ESP8266 modules are newer and less fussy. See the user manual's Troubleshooting section for details.

### Earlier: v0.2.3

- **RN131: Get WiFi Address and home-network setup now work.** On RN131 modules these never completed — the app opened the pass-through to the module but never switched the module itself into command mode, so no address came back. Both now work, and the module is returned to its normal mode afterwards.
- **Fast Server (Envision) boot control** on the Configuration tab, for ESP32/ESP8266 modules on current firmware — plus interlocks so Fast Server no longer interferes with firmware uploads or network setup.
- **Type commands directly in the Command Console**, and steadier serial connect/disconnect and post-upload reconnect.

### Earlier: v0.2.2

- **Consistent rendering across Windows and Qt versions.** The app pins Qt's "Fusion" widget style at startup, so the interface paints the same on every machine regardless of Windows version or Qt build. This removes the native-style variability that could leave the **Network tab blank** for some Windows users.

## Features

- Serial and WiFi command paths for PMC-Eight configuration commands.
- Configuration read/write interface.
- Network tab for ESP32, ESP8266, and RN131 WiFi address/configuration workflows.
- Direct PMC-Eight command console.
- Response log.
- Firmware upload workflow using the bundled Propeller uploader path.
- Startup asset preflight for required files and bundled manuals.

## Requirements

- Python 3.10 or newer
- PyQt6
- pyserial
- A PMC-Eight controller connected by USB serial or reachable over the local network

## Windows

For the packaged ZIP, run `run_dashboard_windows.bat`.

For source/manual runs:

```powershell
py -m pip install -r requirements.txt
py PMC8_Dashboard.py
```

The Windows launcher does not require Administrator mode. It looks for `py`, then `python`, then `python3`. If none are found, install Python 3.10 or newer from python.org and enable **Add python.exe to PATH** during installation, then open a new Command Prompt.

## macOS Packaged ZIP Setup

For most Mac users, `setup_macos.command` is the first file to double-click in the extracted `PMC8_Dashboard_macOS` folder. Setup does the one-time preparation and then launches the dashboard:

- clears Gatekeeper quarantine attributes from the extracted app folder when macOS allows it
- marks `run_PMC8-Dashboard.command`, `run_dashboard_macos.command`, `p1load`, and `run_p1load.sh` executable
- verifies required Python app files, including `network_management.py`
- installs `PyQt6` and `pyserial` from `requirements.txt`
- launches the dashboard through `run_PMC8-Dashboard.command`

After setup succeeds once, the normal day-to-day launcher is `run_PMC8-Dashboard.command`. Double-click that file to start PMC8 Dashboard.

If double-clicking `setup_macos.command` or `run_PMC8-Dashboard.command` opens a text editor, shows a permissions warning, or does nothing, the file probably does not have its Unix executable bit yet. Open Terminal, drag the extracted `PMC8_Dashboard_macOS` folder into Terminal after typing `cd `, press Return, then run:

```bash
sh setup_macos.command
```

That command runs setup even when the file is not clickable yet. To make both command files clickable afterward, run:

```bash
chmod +x setup_macos.command run_PMC8-Dashboard.command
./setup_macos.command
```

The older internal launcher name, `run_dashboard_macos.command`, is still included because `run_PMC8-Dashboard.command` calls it internally.

If setup says Python was not found, install Python 3.10 or newer from python.org, close Terminal, open a new Terminal window, and run `sh setup_macos.command` again.

If setup says a required file is missing, the ZIP was not fully extracted or files were moved out of the folder. Delete the partial folder, extract the ZIP again, and run setup from inside the extracted `PMC8_Dashboard_macOS` folder.

On the first firmware upload, macOS may still block the bundled `p1load` helper. If that happens, open **System Settings > Privacy & Security**, click **Allow Anyway** for `p1load`, run the upload again, and approve the final popup. This is normally a one-time approval.

## macOS Source/Manual Run

```bash
python3 -m pip install -r requirements.txt
python3 PMC8_Dashboard.py
```

## Linux / Raspberry Pi (including 64-bit ARM)

The dashboard is pure Python and runs on Linux, including a **64-bit Raspberry
Pi** (Raspberry Pi OS 64-bit / `aarch64`). **No separate compiled build is
needed** — there is nothing platform-specific to recompile, and the macOS-only
bundled `p1load` binary is not used here. On Linux, firmware upload is handled
by the built-in Python uploader (`p1_loader.py`), so the ARM Pi needs no extra
loader.

### Packaged ZIP (recommended)

Extract `PMC8_Dashboard_Linux.zip`, open the extracted folder in a terminal,
and run the one-time setup:

```bash
./setup_linux.sh
```

Setup installs PyQt6 + pyserial (via `apt` on Raspberry Pi OS, otherwise pip),
adds you to the `dialout` group for serial-port access, then launches the
dashboard. After setup succeeds once, the normal day-to-day launcher is:

```bash
./run_dashboard_linux.sh
```

If a `.sh` file isn't executable (for example the folder was copied instead of
extracted), make them clickable first with
`chmod +x setup_linux.sh run_dashboard_linux.sh`.

### Source / manual run

On Raspberry Pi OS (Bookworm) the system packages avoid building Qt from source:

```bash
sudo apt install python3-pyqt6 python3-serial
python3 PMC8_Dashboard.py
```

Or, on other Linux distros (or in a virtual environment):

```bash
python3 -m pip install -r requirements.txt
python3 PMC8_Dashboard.py
```

Notes:

- **Use a 64-bit OS.** PyQt6 ships wheels/packages for 64-bit ARM (`aarch64`)
  only; 32-bit Raspberry Pi OS is not recommended because PyQt6 is hard to
  install there. `plain pip install PyQt6` may lack a wheel for your Python
  version and try to compile Qt — prefer `apt install python3-pyqt6` on the Pi.
- **Serial port & permissions.** The mount usually appears as `/dev/ttyUSB0`
  (FTDI/CP210x/CH340 adapters) or `/dev/ttyACM0`. Add your user to the
  `dialout` group once so you can open the port without root, then log out and
  back in: `sudo usermod -aG dialout $USER`.
- **This is a desktop (GUI) app.** Run it on the Pi desktop or over VNC/X — not
  from a headless SSH session with no display.

## User Manual

See `docs/PMC8_Dashboard_User_Manual.html` or `docs/PMC8_Dashboard_User_Manual.txt`.

## Third-Party Credits

This project bundles and/or invokes `p1load`, a Propeller loader by dbetz, for firmware loading support.

- Source: https://github.com/dbetz/p1load
- License: MIT License
- Copyright: Copyright (c) 2015 dbetz

See `THIRD_PARTY_NOTICES.md` for the full third-party notice text.
