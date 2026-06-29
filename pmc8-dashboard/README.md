# PMC8 Dashboard v0.2.0

PMC8 Dashboard v0.2.0 is a Python/PyQt6 desktop utility for configuring and testing an Explore Scientific PMC-Eight controller.

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

## User Manual

See `docs/PMC8_Dashboard_User_Manual.html` or `docs/PMC8_Dashboard_User_Manual.txt`.

## Third-Party Credits

This project bundles and/or invokes `p1load`, a Propeller loader by dbetz, for firmware loading support.

- Source: https://github.com/dbetz/p1load
- License: MIT License
- Copyright: Copyright (c) 2015 dbetz

See `THIRD_PARTY_NOTICES.md` for the full third-party notice text.
