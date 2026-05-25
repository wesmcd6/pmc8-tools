PMC8 Dashboard Distribution Notes

Required app files:
- PMC8_Dashboard.py
- PMC8_Configurator.py
- upload_dialog.py
- p1_loader.py
- requirements.txt
- docs\PMC8_Dashboard_User_Manual.html
- docs\PMC8_Dashboard_User_Manual.txt
- assets\
- p1load_package (1)\, when distributing the macOS helper package

Windows:
- Run dist_bundle\run_dashboard_windows.bat, or run:
  py -m pip install -r requirements.txt
  py PMC8_Dashboard.py

macOS:
- Run dist_bundle/run_dashboard_macos.command, or run:
  python3 -m pip install -r requirements.txt
  python3 PMC8_Dashboard.py
- If needed after download, run:
  chmod +x dist_bundle/run_dashboard_macos.command
  xattr -dr com.apple.quarantine /path/to/p1loader

The dashboard performs an asset preflight before opening the GUI. If the preflight reports missing assets, run from the complete distribution folder.


macOS Gatekeeper / p1load approval:
- After extracting the macOS ZIP, run:
  cd /path/to/PMC8_Dashboard_macOS
  xattr -dr com.apple.quarantine .
  chmod +x run_dashboard_macos.command
  chmod +x "p1load_package (1)/p1load"
  ./run_dashboard_macos.command
- On first firmware upload, macOS may still block p1load.
- Open System Settings > Privacy & Security, choose Allow Anyway for p1load, then run the upload again and approve the final popup.
