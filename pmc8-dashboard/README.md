# PMC8 Dashboard

PMC8 Dashboard is a Python/PyQt6 desktop utility for configuring and testing an Explore Scientific PMC-Eight controller.

## Features

- Serial and WiFi command paths for PMC-Eight configuration commands.
- Configuration read/write interface.
- Direct PMC-Eight command console.
- Response log.
- Firmware upload workflow using the bundled Propeller uploader path.
- Startup asset preflight for required files and bundled manuals.

## Requirements

- Python 3.10 or newer
- PyQt6
- pyserial

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

On Windows, use `py` if that is your configured Python launcher:

```powershell
py -m pip install -r requirements.txt
py PMC8_Dashboard.py
```

On macOS:

```bash
python3 -m pip install -r requirements.txt
python3 PMC8_Dashboard.py
```

If using the macOS launcher script and it is not executable:

```bash
chmod +x run_dashboard_macos.command
./run_dashboard_macos.command
```

See `docs/PMC8_Dashboard_User_Manual.html` or `docs/PMC8_Dashboard_User_Manual.txt` for the user manual.

## Third-Party Credits

This project bundles and/or invokes `p1load`, a Propeller loader by dbetz, for firmware loading support.

- Source: https://github.com/dbetz/p1load
- License: MIT License
- Copyright: Copyright (c) 2015 dbetz

See `THIRD_PARTY_NOTICES.md` for the full third-party notice text.

## Windows Python note

The Windows launcher does not require Administrator mode. It looks for `py`, then `python`, then `python3`. If none are found, install Python 3.10 or newer from python.org and enable **Add python.exe to PATH** during installation, then open a new Command Prompt.


## macOS Gatekeeper note

The macOS launcher attempts to set executable permissions, but it cannot fully bypass Gatekeeper quarantine for the bundled `p1load` helper. After extracting the ZIP, run:

```bash
cd /path/to/PMC8_Dashboard_macOS
xattr -dr com.apple.quarantine .
chmod +x run_dashboard_macos.command
chmod +x "p1load_package (1)/p1load"
./run_dashboard_macos.command
```

On first firmware upload, macOS may still require manual approval. If the popup blocks `p1load`, go to System Settings > Privacy & Security, click Allow Anyway for `p1load`, then run the dashboard/upload again and approve the final popup.
