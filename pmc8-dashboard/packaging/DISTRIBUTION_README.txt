PMC8 Dashboard v0.2.2 Distribution Notes

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

Linux / Raspberry Pi (including 64-bit ARM):
- The app is pure Python and runs from source; there is no separate compiled build for Linux or the Raspberry Pi, and the macOS-only p1load helper is not used here (firmware upload uses the built-in Python uploader).
- Use a 64-bit OS (Raspberry Pi OS 64-bit / aarch64); PyQt6 is 64-bit ARM only.
- Extract PMC8_Dashboard_Linux.zip and open the extracted folder in a terminal.
- First run - one-time setup (installs PyQt6 + pyserial, adds you to the dialout group, then launches):
  ./setup_linux.sh
- After setup succeeds once, day-to-day launches use:
  ./run_dashboard_linux.sh
- If a .sh file is not executable (folder copied rather than extracted), run: chmod +x setup_linux.sh run_dashboard_linux.sh
- Manual alternative - Raspberry Pi (recommended, avoids building Qt):
  sudo apt install python3-pyqt6 python3-serial
  python3 PMC8_Dashboard.py
- Manual alternative - other Linux, or a virtual environment:
  python3 -m pip install -r requirements.txt
  python3 PMC8_Dashboard.py
- The serial port is usually /dev/ttyUSB0 or /dev/ttyACM0; setup adds you to the dialout group (takes effect after re-login).
- This is a desktop (GUI) app; run it on the Pi desktop or over VNC/X, not headless.

The dashboard performs an asset preflight before opening the GUI. If the preflight reports missing assets, run from the complete distribution folder.
