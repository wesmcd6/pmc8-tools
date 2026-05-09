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

## Public downloads

For normal users, use the ZIP files attached to the `pmc8-dashboard-v0.1.0` release in the public `pmc8-tools` repository. The ZIPs are release assets rather than committed source files so the repository history stays small and readable.
