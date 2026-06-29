PMC8 Dashboard v0.2.0 Distribution Notes

Required app files:
- PMC8_Dashboard.py
- PMC8_Configurator.py
- network_management.py
- upload_dialog.py
- p1_loader.py
- requirements.txt
- docs\PMC8_Dashboard_User_Manual.html
- docs\PMC8_Dashboard_User_Manual.txt
- assets\
- p1load_package (1)\, when distributing the macOS helper package

Windows:
- Run run_dashboard_windows.bat from the extracted Windows folder.
- If running manually:
  py -m pip install -r requirements.txt
  py PMC8_Dashboard.py

macOS:
- Extract PMC8_Dashboard_macOS.zip.
- Open the extracted PMC8_Dashboard_macOS folder.
- Double-click setup_macos.command first. It clears quarantine where possible, sets executable bits, verifies required Python app files, installs Python requirements, and launches the dashboard through run_PMC8-Dashboard.command.
- After setup succeeds once, double-click run_PMC8-Dashboard.command for normal launches.
- If either .command file is not clickable, open Terminal in the extracted folder and run:
  sh setup_macos.command
- To make both command files clickable afterward, run:
  chmod +x setup_macos.command run_PMC8-Dashboard.command
- If setup reports a missing file, re-extract the ZIP and run setup from the complete extracted folder.
- If macOS blocks p1load on first firmware upload, open System Settings > Privacy & Security, choose Allow Anyway for p1load, run the upload again, and approve the final popup.

The dashboard performs an asset preflight before opening the GUI. If the preflight reports missing assets, run from the complete distribution folder.
