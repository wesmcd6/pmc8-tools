import sys
import socket
import time
import os
import stat
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DOCS_DIR = APP_DIR / "docs"
ASSETS_DIR = APP_DIR / "assets"
MANUAL_HTML = DOCS_DIR / "PMC8_Dashboard_User_Manual.html"
MANUAL_TXT = DOCS_DIR / "PMC8_Dashboard_User_Manual.txt"
APP_VERSION = "0.2.6"


def _is_readable_file(path):
    return path.is_file() and os.access(path, os.R_OK)


def _ensure_executable(path, warnings):
    if not path.exists() or sys.platform.startswith("win"):
        return
    if os.access(path, os.X_OK):
        return
    try:
        mode = path.stat().st_mode
        path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError as exc:
        warnings.append(f"Could not mark {path.name} executable: {exc}")


def preflight_assets():
    """Validate packaged assets before starting the GUI."""
    errors = []
    warnings = []

    for folder in (DOCS_DIR, ASSETS_DIR):
        if not folder.exists():
            try:
                folder.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                errors.append(f"Could not create {folder}: {exc}")
        elif not folder.is_dir():
            errors.append(f"Expected a folder but found a file: {folder}")

    required_files = [
        APP_DIR / "p1_loader.py",
        APP_DIR / "upload_dialog.py",
        MANUAL_HTML,
        MANUAL_TXT,
    ]
    for asset in required_files:
        if not asset.exists():
            errors.append(f"Missing required asset: {asset}")
        elif not _is_readable_file(asset):
            errors.append(f"Required asset is not readable: {asset}")

    p1load_dir = APP_DIR / "p1load_package (1)"
    p1load_binary = p1load_dir / "p1load"
    p1load_script = p1load_dir / "run_p1load.sh"
    if p1load_dir.exists():
        for helper in (p1load_binary, p1load_script):
            if helper.exists():
                if not _is_readable_file(helper):
                    errors.append(f"Helper asset is not readable: {helper}")
                _ensure_executable(helper, warnings)
    elif sys.platform == "darwin":
        warnings.append("Mac p1load helper folder was not found; firmware upload may require the Python uploader path only.")

    if errors or warnings:
        print("PMC8 Dashboard asset preflight")
        for warning in warnings:
            print(f"Warning: {warning}")
        for error in errors:
            print(f"Error: {error}")

    if errors:
        print("Startup stopped. Restore the missing assets or run from the complete distribution folder.")
        return False
    return True
def print_dependency_help(app_name, missing_package):
    print(f"{app_name} requires {missing_package}, but it is not installed in this Python environment.")
    print("Install the required packages, then run the app again:")
    if sys.platform.startswith("win"):
        print("  py -m pip install PyQt6 pyserial")
        print("  py D:\\p1loader\\PMC8_Dashboard.py")
    elif sys.platform == "darwin":
        print("  python3 -m pip install PyQt6 pyserial")
        print("  cd /path/to/p1loader")
        print("  python3 PMC8_Dashboard.py")
    else:
        print("  python3 -m pip install PyQt6 pyserial")
        print("  cd /path/to/p1loader")
        print("  python3 PMC8_Dashboard.py")

try:
    import serial
    import serial.tools.list_ports
except ModuleNotFoundError as exc:
    if exc.name == "serial":
        print_dependency_help("PMC8 Dashboard", "pyserial")
        sys.exit(1)
    raise

try:
    from PyQt6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
        QComboBox, QTextEdit, QFormLayout, QLineEdit, QHBoxLayout, QGridLayout, QSpacerItem, QSizePolicy,
        QGridLayout, QDialog, QFileDialog, QCheckBox, QScrollArea, QTabWidget
    )
    from PyQt6.QtGui import QTextCursor
except ModuleNotFoundError as exc:
    if exc.name == "PyQt6":
        print_dependency_help("PMC8 Dashboard", "PyQt6")
        sys.exit(1)
    raise
from p1_loader import upload
from upload_dialog import UploadDialog
from network_management import NetworkManagementMixin






# Command definitions (ESSi! is built dynamically and hidden until config is populated)
COMMANDS = {
    "ESGpA!": {
        "desc": "Get axis A position motor counts. A = 0 (RA) or 1 (DEC)",
        "template": "ESGp{A}!",
        "params": [{"name": "A", "label": "Axis (0 for RA, 1 for DEC)"}]
    },
    "ESGrA!": {
        "desc": "Get axis A rate (motor counts per second, low resolution). A = 0 or 1",
        "template": "ESGr{A}!",
        "params": [{"name": "A", "label": "Axis (0 for RA, 1 for DEC)"}]
    },
    "ESGtA!": {
        "desc": "Get current target position (motor counts) for axis A. A = 0 or 1",
        "template": "ESGt{A}!",
        "params": [{"name": "A", "label": "Axis (0 for RA, 1 for DEC)"}]
    },
    "ESGdA!": {
        "desc": "Get current axis A direction. A = 0 or 1",
        "template": "ESGd{A}!",
        "params": [{"name": "A", "label": "Axis (0 for RA, 1 for DEC)"}]
    },
    "ESGv!": {
        "desc": "Get firmware version",
        "template": "ESGv!",
        "params": []
    },
    "ESGfA!": {
        "desc": "Get sidereal rate fraction for axis A. A = 0 or 1",
        "template": "ESGf{A}!",
        "params": [{"name": "A", "label": "Axis (0 for RA, 1 for DEC)"}]
    },
    "ESGcA!": {
        "desc": "Get motor current value for track or slew (0 = Slew, 1 = Track)",
        "template": "ESGc{A}!",
        "params": [{"name": "A", "label": "Mode (0 for Slew, 1 for Track)"}]
    },
    "ESGw!": {
        "desc": "Get WiFi channel",
        "template": "ESGw!",
        "params": []
    },
    "ESGq!": {
        "desc": "Get pulseguide state (returns pulseguide for motor 0 and 1)",
        "template": "ESGq!",
        "params": []
    },
    "ESGx!": {
        "desc": "Get current tracking rate value (RA only, high resolution)",
        "template": "ESGx!",
        "params": []
    },
    "ESSpAYYYYYY!": {
        "desc": "Set axis A position value. A = 0 or 1; YYYYYY is hex (6 digits)",
        "template": "ESSp{A}{value}!",
        "params": [
            {"name": "A", "label": "Axis (0 for RA, 1 for DEC)"},
            {"name": "value", "label": "Position (6 hex digits)"}
        ]
    },
    "ESSrAXXXX!": {
        "desc": "Set rate value for axis A. XXXX is hex. A = 0/1 (low res) or 4/5 (high res)",
        "template": "ESSr{A}{value}!",
        "params": [
            {"name": "A", "label": "Axis (0/1 for low res, 4/5 for high res)"},
            {"name": "value", "label": "Rate (4 hex digits)"}
        ]
    },
    "ESSdAD!": {
        "desc": "Set direction for axis A. D = 0 or 1",
        "template": "ESSd{A}{D}!",
        "params": [
            {"name": "A", "label": "Axis (0 for RA, 1 for DEC)"},
            {"name": "D", "label": "Direction (0 or 1)"}
        ]
    },
    "ESSfAXXXX!": {
        "desc": "Set sidereal rate fraction for axis A. A = 0 (RA) or 1 (DEC), XXXX is hex (0 < value <= 100)",
        "template": "ESSf{A}{value}!",
        "params": [
            {"name": "A", "label": "Axis (0 for RA, 1 for DEC)"},
            {"name": "value", "label": "Sidereal rate fraction (4 hex digits)"}
        ]
    },
    "ESScAZZZZ!": {
        "desc": "Set motor current value. A = 0 (Slew), 1 (Track); ZZZZ is current in decimal mA",
        "template": "ESSc{A}{current}!",
        "params": [
            {"name": "A", "label": "Mode (0 for Slew, 1 for Track)"},
            {"name": "current", "label": "Current (in decimal, e.g., 0123)"}
        ]
    },
    "ESSwDD!": {
        "desc": "Set WiFi channel. DD is decimal (0-11)",
        "template": "ESSw{channel}!",
        "params": [{"name": "channel", "label": "WiFi Channel (0-11)"}]
    },
    "ESSqADHHHH!": {
        "desc": "Pulse rate command. A = Axis (0 for RA, 1 for DEC), D = Direction (0 or 1), HHHH is hex time (ms)",
        "template": "ESSq{A}{D}{time}!",
        "params": [
            {"name": "A", "label": "Axis (0 for RA, 1 for DEC)"},
            {"name": "D", "label": "Direction (0 or 1)"},
            {"name": "time", "label": "Time (4 hex digits)"}
        ]
    },
    "ESTrXXXX!": {
        "desc": "Set RA tracking rate value (High precision, 25x desired pulse rate)",
        "template": "ESTr{value}!",
        "params": [{"name": "value", "label": "RA tracking rate (4 hex digits)"}]
    },
    "ESTeAXXXX!": {
        "desc": "Set tracking rate for axis A (High precision, 25x desired pulse rate)",
        "template": "ESTe{A}{value}!",
        "params": [
            {"name": "A", "label": "Axis (0 for RA, 1 for DEC)"},
            {"name": "value", "label": "Tracking rate (4 hex digits)"}
        ]
    },
    "ESPtAYYYYYY!": {
        "desc": "Point (slew) to target in axis A using ramps. YYYYYY is motor counts in hex.",
        "template": "ESPt{A}{value}!",
        "params": [
            {"name": "A", "label": "Axis (0 for RA, 1 for DEC)"},
            {"name": "value", "label": "Target position (6 hex digits)"}
        ]
    },
    "ESV!": {
        "desc": "Request motor state vector.",
        "template": "ESV!",
        "params": []
    },
    "ESH!": {
        "desc": "Toggle Northern/Southern Hemisphere (1 = Northern, 0 = Southern).",
        "template": "ESH!",
        "params": []
    },
    "ESM!": {
        "desc": "Toggle Enable sidereal rate at boot (0 = boot stopped, 1 = boot RA at sidereal).",
        "template": "ESM!",
        "params": []
    },
    "ESW!": {
        "desc": "Toggle Enable/Disable comms watchdog (1 = continue tracking, 0 = stop on lost comms).",
        "template": "ESW!",
        "params": []
    },
    "ESY!": {
        "desc": "Toggle IP protocol (0 = TCP, 1 = UDP).",
        "template": "ESY!",
        "params": []
    },
    "ESB!": {
        "desc": "Boot PMC-Eight Controller.",
        "template": "ESB!",
        "params": []
    },
    "ESGi!": {
        "desc": "Retrieve all PMC8 Configuration settings",
        "template": "ESGi!",
        "params": []
    },
    "ESGe!": {
        "desc": "Get Envision (Fast Server) status. 3-bit field: 1 = capable, 2 = boot flag, 4 = currently on",
        "template": "ESGe!",
        "params": []
    },
    "ESSe<p>!": {
        "desc": "Set Envision (Fast Server). p = 0 (stop now), 1 (start now), 3 (boot on), 4 (boot off)",
        "template": "ESSe{p}!",
        "params": [{"name": "p", "label": "Value (0 = stop, 1 = start, 3 = boot on, 4 = boot off)"}]
    },
    "ESSi!": {
        "desc": "Set PMC8 Configuration settings (computed from fields)",
        "template": "",  # Built dynamically.
        "params": []
    }
}

class PMC8Configurator(NetworkManagementMixin, QWidget):
    def __init__(self):
        super().__init__()
        self.param_widgets = {}      # For command parameters.
        self.config_widgets = {}     # For configuration display.
        self.config_populated = False
        self.connection_socket = None  # For WiFi connections.
        self.serial_port = None      # For serial connections.
        # Fast Server (WiFi fast-server boot) state, populated by Get Configuration.
        self._wifi_type = None       # "RN131" / "8266" / "ESP32" / "Unknown"
        self._fast_server_state = None   # last ESGe! digit: 0/1/2 or None
        self._fast_server_available = False  # True when the boot option can be set
        self.initUI()

    def initUI(self):
        self.setWindowTitle(f"PMC-Eight Dashboard v{APP_VERSION}")
        self.resize(960, 820)
        self.setMinimumSize(660, 520)
        self.resize(720, 764)

        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        page = QWidget()
        main_layout = QVBoxLayout(page)
        main_layout.setContentsMargins(14, 8, 14, 8)
        main_layout.setSpacing(6)

        title = QLabel(f"PMC-Eight Dashboard v{APP_VERSION}")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Configuration, command console, Network tools, and Propeller firmware upload")
        subtitle.setObjectName("SubtitleLabel")
        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # Connection panel
        connection_panel = QWidget()
        connection_panel.setObjectName("Panel")
        connection_layout = QVBoxLayout(connection_panel)
        connection_layout.setContentsMargins(12, 6, 12, 6)
        connection_layout.setSpacing(8)
        connection_header = QLabel("Connection")
        connection_header.setObjectName("SectionHeader")
        connection_layout.addWidget(connection_header)

        connection_grid = QGridLayout()
        connection_grid.setHorizontalSpacing(10)
        connection_grid.setVerticalSpacing(8)
        connection_layout.addLayout(connection_grid)

        type_label = QLabel("Type")
        type_label.setMinimumWidth(76)
        self.connection_type_combo = QComboBox()
        self.connection_type_combo.setMinimumWidth(150)
        self.connection_type_combo.addItems(["Serial", "WiFi"])
        self.connection_type_combo.currentIndexChanged.connect(self.update_connection_ui)
        connection_grid.addWidget(type_label, 0, 0)
        connection_grid.addWidget(self.connection_type_combo, 0, 1)

        self.serial_port_label = QLabel("Serial Port")
        self.serial_port_label.setMinimumWidth(76)
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(240)
        self.refresh_ports()
        connection_grid.addWidget(self.serial_port_label, 1, 0)
        connection_grid.addWidget(self.port_combo, 1, 1, 1, 3)

        self.ip_label = QLabel("IP Address")
        self.ip_label.setMinimumWidth(76)
        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("192.168.47.1")
        self.ip_edit.setMinimumWidth(180)
        connection_grid.addWidget(self.ip_label, 2, 0)
        connection_grid.addWidget(self.ip_edit, 2, 1)

        self.port_label = QLabel("Port")
        self.port_edit = QLineEdit()
        self.port_edit.setPlaceholderText("54372")
        self.port_edit.setText("54372")
        self.port_edit.setReadOnly(True)
        self.port_edit.setFixedWidth(100)
        connection_grid.addWidget(self.port_label, 2, 2)
        connection_grid.addWidget(self.port_edit, 2, 3)

        self.protocol_label = QLabel("Protocol")
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["TCP", "UDP"])
        self.protocol_combo.setFixedWidth(120)
        connection_grid.addWidget(self.protocol_label, 2, 4)
        connection_grid.addWidget(self.protocol_combo, 2, 5)
        connection_grid.setColumnStretch(1, 1)

        button_row = QHBoxLayout()
        button_row.setSpacing(12)
        self.connect_button = QPushButton("Connect")
        self.connect_button.setObjectName("PrimaryButton")
        self.connect_button.clicked.connect(self.connect_device)
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_device)
        self.disconnect_button.setEnabled(False)   # nothing connected at startup
        self.refresh_button = QPushButton("Refresh Ports")
        self.refresh_button.clicked.connect(self.refresh_ports)
        button_row.addWidget(self.connect_button)
        button_row.addWidget(self.disconnect_button)
        button_row.addWidget(self.refresh_button)
        button_row.addStretch(1)
        connection_layout.addLayout(button_row)
        main_layout.addWidget(connection_panel)

        # Configuration actions panel
        actions_panel = QWidget()
        actions_panel.setObjectName("Panel")
        actions_layout = QVBoxLayout(actions_panel)
        actions_layout.setContentsMargins(12, 6, 12, 6)
        actions_layout.setSpacing(8)
        actions_header = QLabel("Configuration Actions")
        actions_header.setObjectName("SectionHeader")
        actions_layout.addWidget(actions_header)
        action_buttons = QHBoxLayout()
        action_buttons.setSpacing(12)
        self.get_config_button = QPushButton("Get Configuration")
        self.get_config_button.setObjectName("PrimaryButton")
        self.get_config_button.clicked.connect(self.get_configuration)
        self.save_config_button = QPushButton("Save Configuration")
        self.save_config_button.clicked.connect(self.save_configuration)
        self.save_config_button.setEnabled(False)
        self.boot_pmc8_button = QPushButton("Boot PMC8")
        self.boot_pmc8_button.setObjectName("DangerButton")
        self.boot_pmc8_button.clicked.connect(self.boot_pmc8)
        action_buttons.addWidget(self.get_config_button)
        action_buttons.addWidget(self.save_config_button)
        action_buttons.addWidget(self.boot_pmc8_button)
        action_buttons.addStretch(1)
        actions_layout.addLayout(action_buttons)
        main_layout.addWidget(actions_panel)

        # Command console panel
        command_panel = QWidget()
        command_panel.setObjectName("Panel")
        command_layout = QVBoxLayout(command_panel)
        command_layout.setContentsMargins(12, 6, 12, 6)
        command_layout.setSpacing(8)
        command_header = QLabel("Command Console")
        command_header.setObjectName("SectionHeader")
        command_layout.addWidget(command_header)
        # Two separate inputs on purpose: this combo picks from the known-command
        # list, and the raw box below types anything else. It used to be a single
        # editable combo doing both jobs, but on macOS the embedded line edit
        # never took a click — every click just dropped the list, so a raw command
        # could not be typed at all. A plain QLineEdit is predictable everywhere,
        # and it also means the list selection no longer has to be reverse-
        # engineered from the visible text (see _resolve_command_to_send).
        self.command_combo = QComboBox()
        self.command_combo.setObjectName("CommandCombo")
        # Don't let the longest item ("ESGi! - Retrieve all …") force the whole
        # window wide. Size to a modest content length; it still fills the panel
        # width and the dropdown popup shows full item text.
        self.command_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.command_combo.setMinimumContentsLength(22)
        self.update_command_dropdown()
        self.command_combo.currentIndexChanged.connect(self.update_command_description)
        self.command_combo.currentIndexChanged.connect(lambda: self.update_param_fields(self.command_combo.currentData()))
        command_layout.addWidget(self.command_combo)

        self.command_desc_label = QLabel("Command Description")
        self.command_desc_label.setObjectName("HelpLabel")
        self.command_desc_label.setWordWrap(True)
        command_layout.addWidget(self.command_desc_label)
        if self.command_combo.count() > 0:
            initial_key = self.command_combo.itemData(0)
            self.command_desc_label.setText(f"Description: {COMMANDS[initial_key]['desc']}")

        self.param_area = QWidget()
        self.param_layout = QFormLayout()
        self.param_layout.setContentsMargins(0, 4, 0, 4)
        self.param_layout.setHorizontalSpacing(12)
        self.param_layout.setVerticalSpacing(10)
        self.param_area.setLayout(self.param_layout)
        command_layout.addWidget(self.param_area)

        # Raw command entry — always available, and takes precedence over the
        # list whenever it has text (see _resolve_command_to_send). Enter sends.
        raw_row = QHBoxLayout()
        raw_row.setSpacing(8)
        raw_label = QLabel("Or type a command:")
        self.raw_command_edit = QLineEdit()
        self.raw_command_edit.setObjectName("RawCommandEdit")
        self.raw_command_edit.setClearButtonEnabled(True)
        self.raw_command_edit.setPlaceholderText("e.g. ESGe!  — overrides the selection above when not empty")
        self.raw_command_edit.returnPressed.connect(self.send_command)
        raw_row.addWidget(raw_label)
        raw_row.addWidget(self.raw_command_edit, 1)
        command_layout.addLayout(raw_row)

        self.send_button = QPushButton("Send Command")
        self.send_button.clicked.connect(self.send_command)
        command_layout.addWidget(self.send_button)
        main_layout.addWidget(command_panel)

        # Response log panel
        response_panel = QWidget()
        response_panel.setObjectName("Panel")
        response_layout = QVBoxLayout(response_panel)
        response_layout.setContentsMargins(12, 6, 12, 6)
        response_layout.setSpacing(8)
        response_header = QLabel("Response Log")
        response_header.setObjectName("SectionHeader")
        response_layout.addWidget(response_header)
        self.response_box = QTextEdit()
        self.response_box.setReadOnly(True)
        self.response_box.setMinimumHeight(130)
        response_layout.addWidget(self.response_box)
        main_layout.addWidget(response_panel)

        # Configuration settings panel
        config_panel = QWidget()
        config_panel.setObjectName("Panel")
        config_layout = QVBoxLayout(config_panel)
        config_layout.setContentsMargins(12, 6, 12, 6)
        config_layout.setSpacing(8)
        config_header = QLabel("Configuration Settings")
        config_header.setObjectName("SectionHeader")
        config_layout.addWidget(config_header)
        self.config_grid = QGridLayout()
        self.config_grid.setHorizontalSpacing(14)
        self.config_grid.setVerticalSpacing(6)
        # Pack the label/value pairs to the left: give a trailing column all the
        # slack so the label columns shrink to their text instead of stretching
        # wide across the panel (that was the "ton of room" after the labels).
        self.config_grid.setColumnStretch(4, 1)
        config_layout.addLayout(self.config_grid)

        # Fast Server (WiFi fast-server boot) — persistent sub-section. Populated
        # by Get Configuration (ESGe!) and applied by Save Configuration
        # (ESSe3! = boot on / ESSe4! = boot off). Not part of the ESGi/ESSi payload.
        fast_server_grid = QGridLayout()
        fast_server_grid.setHorizontalSpacing(24)
        fast_server_grid.setVerticalSpacing(6)
        self.fast_server_status_caption = QLabel("Fast Server Status:")
        self.fast_server_status_label = QLabel("—")
        self.fast_server_checkbox = QCheckBox("Boot into Fast Server")
        self.fast_server_checkbox.setObjectName("BootCheck")
        self.fast_server_hint = QLabel("")
        self.fast_server_hint.setObjectName("HelpLabel")
        self.fast_server_hint.setWordWrap(True)
        fast_server_grid.addWidget(self.fast_server_status_caption, 0, 0)
        fast_server_grid.addWidget(self.fast_server_status_label, 0, 1)
        fast_server_grid.addWidget(self.fast_server_checkbox, 1, 0, 1, 2)
        fast_server_grid.addWidget(self.fast_server_hint, 2, 0, 1, 2)
        config_layout.addSpacing(6)
        config_layout.addLayout(fast_server_grid)
        self._fast_server_reset()

        main_layout.addWidget(config_panel)

        # Firmware upload panel
        upload_panel = QWidget()
        upload_panel.setObjectName("Panel")
        upload_layout = QVBoxLayout(upload_panel)
        upload_layout.setContentsMargins(12, 6, 12, 6)
        upload_layout.setSpacing(12)
        upload_header = QLabel("Firmware Upload")
        upload_header.setObjectName("SectionHeader")
        upload_layout.addWidget(upload_header)
        upload_buttons = QHBoxLayout()
        self.upload_button = QPushButton("Upload Propeller Code")
        self.upload_button.clicked.connect(self.open_upload_dialog)
        self.upload_status_label = QLabel("")
        self.upload_status_label.setObjectName("HelpLabel")
        upload_buttons.addWidget(self.upload_button)
        upload_buttons.addWidget(self.upload_status_label)
        upload_buttons.addStretch(1)
        upload_layout.addLayout(upload_buttons)
        main_layout.addWidget(upload_panel)

        main_layout.addStretch(1)
        scroll.setWidget(page)

        # Tabs: existing UI becomes the "Configurator" tab; add the "Network" tab.
        self.tabs = QTabWidget()
        self.tabs.addTab(scroll, "Configurator")
        self.tabs.addTab(self.build_network_tab(), "Network")
        outer_layout.addWidget(self.tabs)
        self.setLayout(outer_layout)
        self.update_param_fields(self.command_combo.currentData())
        self.update_connection_ui()
        self._apply_modern_style()

    def _apply_modern_style(self):
        self.setStyleSheet("""
            QWidget {
                background: #0f1720;
                color: #e8eef5;
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 10.5pt;
            }
            QLabel#TitleLabel {
                font-size: 16pt;
                font-weight: 700;
                color: #ffffff;
            }
            QLabel#SubtitleLabel, QLabel#HelpLabel {
                color: #9fb0c2;
            }
            QLabel#SectionHeader {
                font-size: 11pt;
                font-weight: 700;
                color: #cfe2f5;
                padding-bottom: 1px;
            }
            QWidget#Panel {
                background: #15202b;
                border: 1px solid #27384a;
                border-radius: 8px;
            }
            QLineEdit, QComboBox, QTextEdit {
                min-height: 26px;
                background: #0b1118;
                border: 1px solid #31465c;
                border-radius: 6px;
                padding: 4px 8px;
                color: #f3f7fb;
                selection-background-color: #2f7dd3;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border-color: #4aa3ff;
            }
            QLineEdit:read-only {
                color: #b6c4d2;
                background: #101923;
            }
            QPushButton {
                background: #223244;
                border: 1px solid #3a5169;
                border-radius: 6px;
                padding: 3px 14px;
                color: #eef6ff;
                min-height: 20px;
            }
            QPushButton:hover {
                background: #2c4056;
                border-color: #52708f;
            }
            QPushButton:pressed {
                background: #1a2836;
            }
            QPushButton:disabled {
                background: #1a2430;
                color: #647383;
                border-color: #253342;
            }
            QPushButton#PrimaryButton {
                background: #2166a8;
                border-color: #3986d1;
            }
            QPushButton#PrimaryButton:hover {
                background: #2c7cc7;
            }
            QPushButton#ConnectedButton {
                background: #1f8a4c;
                border-color: #33b86b;
            }
            QPushButton#ConnectedButton:hover {
                background: #27a85d;
            }
            QPushButton#DangerButton {
                background: #7d3440;
                border-color: #a84a5a;
            }
            QPushButton#DangerButton:hover {
                background: #963f4d;
            }
            QCheckBox {
                spacing: 8px;
                color: #e8eef5;
            }
            QCheckBox:disabled {
                color: #647383;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #3a5169;
                border-radius: 4px;
                background: #0b1118;
            }
            QCheckBox::indicator:hover {
                border-color: #52708f;
            }
            QCheckBox::indicator:checked {
                background: #2166a8;
                border-color: #3986d1;
            }
            QCheckBox::indicator:disabled {
                border-color: #253342;
                background: #1a2430;
            }
            /* Command console input: clear, bright outline so the editable
               field is obvious whether or not a command is selected. */
            QComboBox#CommandCombo {
                border: 1px solid #4aa3ff;
            }
            QComboBox#CommandCombo:focus {
                border: 1px solid #6bb6ff;
            }
            QLineEdit#RawCommandEdit {
                border: 1px solid #4aa3ff;
            }
            QLineEdit#RawCommandEdit:focus {
                border: 1px solid #6bb6ff;
            }
            /* Boot-into-Fast-Server checkbox: red = off, green = on, so its
               state is unmistakable (the default box was invisible when off). */
            QCheckBox#BootCheck::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #e06c5a;
                background: #4a2320;
            }
            QCheckBox#BootCheck::indicator:checked {
                border: 2px solid #33b86b;
                background: #1f8a4c;
            }
            QCheckBox#BootCheck::indicator:disabled {
                border: 2px solid #4a5560;
                background: #222b34;
            }
            QTabWidget::pane {
                background: #0f1720;
                border: 1px solid #27384a;
                border-radius: 6px;
                top: -1px;
            }
            QTabBar::tab {
                background: #15202b;
                color: #cfe2f5;
                border: 1px solid #27384a;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 18px;
                margin-right: 2px;
                min-width: 90px;
            }
            QTabBar::tab:selected {
                background: #2166a8;
                color: #ffffff;
                border-color: #3986d1;
            }
            QTabBar::tab:hover:!selected {
                background: #1d2c3b;
            }
        """)
    def update_connection_ui(self):
        conn_type = self.connection_type_combo.currentText()
        serial_visible = conn_type == "Serial"
        wifi_visible = not serial_visible

        self.serial_port_label.setVisible(serial_visible)
        self.port_combo.setVisible(serial_visible)

        self.ip_label.setVisible(wifi_visible)
        self.ip_edit.setVisible(wifi_visible)
        self.port_label.setVisible(wifi_visible)
        self.port_edit.setVisible(wifi_visible)
        self.protocol_label.setVisible(wifi_visible)
        self.protocol_combo.setVisible(wifi_visible)

        # When switching to WiFi, pre-fill the IP field if the user hasn't
        # already typed one. Prefer the module's last-known address (captured
        # when they got/set it on the Network tab); otherwise fall back to the
        # ESP boot default. RN131 (or an unknown module) is left blank so its
        # greyed placeholder example shows, as before.
        if wifi_visible and not self.ip_edit.text().strip():
            last_ip = getattr(self, "_net_last_ip", "")
            module = self.net_module_combo.currentText() \
                if getattr(self, "net_module_combo", None) else ""
            if last_ip:
                self.ip_edit.setText(last_ip)
            elif module in ("ESP32", "ESP8266"):
                self.ip_edit.setText("192.168.47.1")


    def set_connection_indicator(self, connected):
        self.connect_button.setObjectName("ConnectedButton" if connected else "PrimaryButton")
        self.connect_button.setText("Connected" if connected else "Connect")
        self.connect_button.style().unpolish(self.connect_button)
        self.connect_button.style().polish(self.connect_button)
        self.connect_button.update()
        # Disconnect is only meaningful when a link is live — grey it out
        # otherwise. Every connect/disconnect path routes through here.
        self.disconnect_button.setEnabled(connected)


    def refresh_ports(self):
        try:
            previous = self.port_combo.currentData()  # remember the user's choice
            self.port_combo.clear()
            self.port_combo.addItem("Select serial port", "")
            ports = list(serial.tools.list_ports.comports())
            if sys.platform == "darwin":
                # macOS provides both /dev/tty.* and /dev/cu.* entries. For an
                # app initiating commands to the mount, /dev/cu.* is the right
                # callout device; /dev/tty.* can open but not behave correctly.
                ports = [port for port in ports if port.device.startswith("/dev/cu.")]
            for port in ports:
                description = port.description or "Serial device"
                if "Bluetooth" in description:
                    continue
                label = f"{port.device} - {description}"
                self.port_combo.addItem(label, port.device)
            # Preserve the user's selection across refreshes; only fall back to
            # the placeholder when the previously chosen port is truly gone.
            idx = self.port_combo.findData(previous) if previous else -1
            self.port_combo.setCurrentIndex(idx if idx >= 0 else 0)
        except Exception as e:
            print(f"Error refreshing ports: {e}")


    def connect_device(self):
        conn_type = self.connection_type_combo.currentText()
        if conn_type == "Serial":
            self.connect_serial()
        else:
            self.connect_wifi()

    def disconnect_device(self):
        # Disconnect whichever transport is actually open, regardless of the
        # connection-type dropdown. The user may switch the dropdown to WiFi
        # (e.g. to see an IP fetched on the Network tab) while still connected
        # over Serial; Disconnect must still tear down the live Serial link —
        # and vice versa. So we key off the real connection state, not the combo.
        disconnected = False
        if self.serial_port and self.serial_port.is_open:
            self.disconnect_serial()
            disconnected = True
        if self.connection_socket:
            self.disconnect_wifi()
            disconnected = True
        if not disconnected:
            self.response_box.append("Not connected.")
            self.scroll_response_to_bottom()

    def connect_serial(self):
        port = (self.port_combo.currentData() or "").strip()
        if not port:
            self.response_box.append("No serial port selected.")
            self.scroll_response_to_bottom()
            return
        try:
            self.response_box.append(f"Attempting to connect to {port}...")
            self.serial_port = serial.Serial()
            self.serial_port.port = port
            self.serial_port.baudrate = 115200
            self.serial_port.timeout = 1
            self.serial_port.write_timeout = 1
            self.serial_port.xonxoff = False
            self.serial_port.rtscts = False
            self.serial_port.dsrdtr = False

            # Keep reset/boot control lines inactive before opening.
            # Setting the stored state before open is the pyserial equivalent
            # of .NET SerialPort DtrEnable/RtsEnable = false before Open().
            self.serial_port._dtr_state = False
            self.serial_port._rts_state = False
            self.serial_port.dtr = False
            self.serial_port.rts = False
            self.serial_port.open()
            self.response_box.append(f"Connected to {port} (Serial, DTR/RTS held low)")
            self.set_connection_indicator(True)
            # On Linux the kernel asserts DTR when the tty is opened (unlike
            # Windows/macOS, which honour the pre-open "DTR off"), and DTR is
            # tied to the Propeller reset — so every serial connect reboots the
            # mount. It comes right back, so just wait for it before handing
            # control back. No-op on platforms that don't reset.
            if sys.platform.startswith("linux"):
                self._wait_for_mount_after_reset()
        except Exception as e:
#            self.response_box.append(f"Failed to connect (Serial): {e}")
             self.response_box.append("Please select the PMC-Eight COM port")
             # Keep the user's port selection on a failed connect so they can
             # simply retry — do NOT reset the dropdown.
             self.set_connection_indicator(False)

        finally:
            self.scroll_response_to_bottom()

    def _wait_for_mount_after_reset(self, timeout=25.0):
        """After a Linux serial connect, the DTR pulse reboots the PMC-Eight.
        Poll ESGi! until it answers so the reset is transparent — the connect
        just takes a few seconds longer while the mount restarts. The probe uses
        ESGi!, so once the mount is back we reuse that reply to fill the config
        fields and then send ESGe! for the Fast Server fields — the connect
        doubles as Get Configuration. Keeps the GUI responsive and gives up
        after `timeout` seconds (the user can retry Get Configuration)."""
        self.response_box.append("Mount reboots on serial connect (Linux) — waiting for it to come back...")
        self.scroll_response_to_bottom()
        end = time.time() + timeout
        while time.time() < end:
            try:
                resp = self._serial_send_command("ESGi!", timeout=1.5)
            except Exception:  # noqa: BLE001 - port may be mid-reboot
                resp = ""
            if resp and resp.startswith("ESGi"):
                config = self.parse_ESGi_response(resp)
                if config:  # a full, valid reply — mount is up
                    self.response_box.append("Mount is back up — filling configuration.")
                    self.update_config_display(config)
                    self._wifi_type = config.get("WiFi Type")
                    self.save_config_button.setEnabled(True)
                    # Finish the fields with the Fast Server state (ESGe!);
                    # skipped for RN131, tolerated when unanswered.
                    self._fast_server_refresh(lambda c: self._serial_send_command(c, timeout=5.0))
                    self.scroll_response_to_bottom()
                    return True
            QApplication.processEvents()
            time.sleep(0.3)
        self.response_box.append("Mount didn't answer within the wait — it may still be "
                                 "starting. Try Get Configuration in a moment.")
        self.scroll_response_to_bottom()
        return False

    def disconnect_serial(self):
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
                self.response_box.append("Serial port disconnected.")
        except Exception as e:
            self.response_box.append(f"Error disconnecting (Serial): {e}")
        finally:
            # Always clear state + button, even if the port was already closed
            # (device re-enumerated, cable pulled) — otherwise the button stays
            # "Connected" for a dead link. Leave a live WiFi link's indicator be.
            self.serial_port = None
            if not self.connection_socket:
                self.set_connection_indicator(False)
            self.scroll_response_to_bottom()

    def connect_wifi(self):
        ip = self.ip_edit.text().strip()
        port_text = self.port_edit.text().strip()
        proto = self.protocol_combo.currentText().strip()
        if not ip or not port_text:
            self.response_box.append("IP address and port must be provided for WiFi connection.")
            self.scroll_response_to_bottom()
            return
        try:
            port = int(port_text)
        except ValueError:
            self.response_box.append("Port must be an integer.")
            self.scroll_response_to_bottom()
            return
        try:
            self.response_box.append(f"Attempting to connect to {ip}:{port} via {proto}...")
            if proto == "TCP":
                self.connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.connection_socket.settimeout(3.0)
                self.connection_socket.connect((ip, port))
            else:
                self.connection_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.connection_socket.settimeout(3.0)
                self.connection_socket.connect((ip, port))
            self.response_box.append(f"Connected to {ip}:{port} ({proto})")
            self.set_connection_indicator(True)
        except Exception as e:
            self.response_box.append(f"Failed to connect (WiFi): {e}")
            self.set_connection_indicator(False)
        finally:
            self.scroll_response_to_bottom()

    def disconnect_wifi(self):
        try:
            if self.connection_socket:
                self.connection_socket.close()
                self.response_box.append("WiFi connection disconnected.")
        except Exception as e:
            self.response_box.append(f"Error disconnecting (WiFi): {e}")
        finally:
            # Always clear state + button, even if the socket was already dead.
            self.connection_socket = None
            if not (self.serial_port and self.serial_port.is_open):
                self.set_connection_indicator(False)
            self.scroll_response_to_bottom()

    def _serial_send_command(self, cmd, timeout=3.0):
        if not self.serial_port or not self.serial_port.is_open:
            raise RuntimeError("Serial port not connected")

        original_timeout = self.serial_port.timeout
        try:
            self.serial_port.timeout = 0.1
            self.serial_port.reset_input_buffer()

            # Serial PMC-Eight command handling expects the command terminator
            # plus CR/LF framing. WiFi uses raw commands; serial keeps CR/LF.
            self.serial_port.write((cmd + "\r\n").encode("ascii"))
            self.serial_port.flush()

            echo = cmd.strip()
            frames = []
            frame = bytearray()
            raw = bytearray()
            deadline = time.time() + timeout
            last_data_time = None

            while time.time() < deadline:
                data = self.serial_port.read(1)
                if not data:
                    if raw and last_data_time and time.time() - last_data_time > 0.35:
                        break
                    continue

                raw.extend(data)
                frame.extend(data)
                last_data_time = time.time()

                if data not in (b"!", b"\n"):
                    continue

                response = bytes(frame).decode("ascii", errors="replace").strip()
                response = response.strip("\r\n")
                es_idx = response.find("ES")
                if es_idx > 0:
                    response = response[es_idx:]
                if response:
                    frames.append(response)
                    if response != echo:
                        return response
                frame.clear()

            if frame:
                response = bytes(frame).decode("ascii", errors="replace").strip()
                response = response.strip("\r\n")
                es_idx = response.find("ES")
                if es_idx > 0:
                    response = response[es_idx:]
                if response:
                    return response

            if frames:
                return frames[-1]

            # Last resort: show any raw bytes received so the transaction window
            # is useful during hardware diagnosis.
            raw_text = bytes(raw).decode("ascii", errors="replace").strip()
            return raw_text if raw_text else f"[no bytes received from {self.serial_port.port}]"
        finally:
            self.serial_port.timeout = original_timeout
            self.serial_port.reset_input_buffer()
    def _wifi_send_command(self, cmd, timeout=3.0):
        if not self.connection_socket:
            raise RuntimeError("WiFi connection not established")

        proto = self.protocol_combo.currentText().strip().upper()
        sock = self.connection_socket
        sock.settimeout(timeout)

        # PMC-Eight WiFi commands are already terminated by '!'. Do not append
        # CR/LF here; raw TCP/UDP bridges can treat those as extra bytes.
        payload = cmd.encode("ascii")
        if proto == "TCP":
            sock.sendall(payload)
        else:
            sock.send(payload)

        chunks = []
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                chunk = sock.recv(1024)
            except socket.timeout:
                break
            if not chunk:
                break
            chunks.append(chunk)
            if b"!" in chunk or b"!" in b"".join(chunks):
                break
            if proto == "UDP":
                break

        if not chunks:
            # Old firmware silently ignores commands it doesn't implement
            # (e.g. ESGe!/ESSe* on a mount without Fast Server) — no reply at
            # all. Treat a missing reply as an empty response, NOT an error, so
            # an unanswered command never looks like a dropped connection. The
            # socket stays open; the caller just gets "" and moves on.
            return ""

        response = b"".join(chunks).decode("ascii", errors="replace").strip()
        bang = response.find("!")
        if bang >= 0:
            response = response[:bang + 1]
        es_idx = response.find("ES")
        if es_idx > 0:
            response = response[es_idx:]
        return response

    def update_command_dropdown(self):
        self.command_combo.clear()
        for key, info in COMMANDS.items():
            if key == "ESSi!" and not self.config_populated:
                continue
            display_text = f"{key} - {info['desc']}"
            self.command_combo.addItem(display_text, key)

    def update_command_description(self):
        command_key = self.command_combo.currentData()
        if command_key in COMMANDS:
            desc = COMMANDS[command_key]['desc']
            self.command_desc_label.setText(f"Description: {desc}")
        else:
            self.command_desc_label.setText("Command Description:")

    def update_param_fields(self, command_key):
        while self.param_layout.count():
            child = self.param_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.param_widgets = {}
        command_info = COMMANDS.get(command_key, {})
        params = command_info.get("params", [])
        if not params:
            self.param_area.setVisible(False)
        else:
            self.param_area.setVisible(True)
            for param in params:
                label_text = param.get("label", param["name"])
                line_edit = QLineEdit()
                self.param_widgets[param["name"]] = line_edit
                self.param_layout.addRow(label_text + ":", line_edit)

    def _resolve_command_to_send(self):
        """Return (cmd_string, command_key) to transmit. `command_key` is the
        known-command key when the list selection was used, else None for a
        free-typed raw command. Returns (None, None) on error/empty.

        The raw box wins whenever it holds text — it's the deliberate "send
        exactly this" escape hatch, so an empty box is the only way to mean
        "use the list". Clear it to go back to the dropdown."""
        typed = self.raw_command_edit.text().strip()
        if typed:
            return typed, None

        idx = self.command_combo.currentIndex()
        if idx < 0:
            self.response_box.append("Select a command, or type one in the box below the list.")
            self.scroll_response_to_bottom()
            return None, None
        command_key = self.command_combo.itemData(idx)
        if command_key == "ESSi!":
            return self.build_config_command(), command_key  # cmd may be None
        info = COMMANDS.get(command_key, {})
        template = info.get("template", "")
        params = {}
        for param in info.get("params", []):
            name = param["name"]
            value = self.param_widgets[name].text().strip()
            if not value:
                self.response_box.append(f"Parameter '{name}' is required.")
                self.scroll_response_to_bottom()
                return None, None
            params[name] = value
        try:
            return (template.format(**params) if template else command_key), command_key
        except KeyError as e:
            self.response_box.append(f"Missing parameter: {e}")
            self.scroll_response_to_bottom()
            return None, None

    def send_command(self):
        conn_type = self.connection_type_combo.currentText()
        if conn_type == "Serial" and not (self.serial_port and self.serial_port.is_open):
            self.response_box.append("Serial port not connected.")
            self.scroll_response_to_bottom()
            return
        if conn_type != "Serial" and not self.connection_socket:
            self.response_box.append("WiFi connection not established.")
            self.scroll_response_to_bottom()
            return

        cmd, command_key = self._resolve_command_to_send()
        if not cmd:
            return

        if conn_type == "Serial":
            self.serial_port.reset_input_buffer()
            response = self._serial_send_command(cmd)
        else:
            try:
                response = self._wifi_send_command(cmd)
            except Exception as e:
                self.response_box.append(f"Error during send/receive (WiFi): {e}")
                self.scroll_response_to_bottom()
                return
        self.response_box.append(f"Sent: {cmd}\nReceived: {response}")
        self.scroll_response_to_bottom()

        # ESGi! refreshes the config display — whether it was picked from the
        # list (command_key set) or typed as a raw command (command_key None).
        if command_key == "ESGi!" or cmd.strip() == "ESGi!":
            config = self.parse_ESGi_response(response)
            self.update_config_display(config)
            self._wifi_type = config.get("WiFi Type")
            self.save_config_button.setEnabled(True)
        # A manually-sent ESGe! with a valid reply updates the Fast Server
        # display too (skip on RN131, which has no Fast Server).
        elif cmd.strip() == "ESGe!" and not self._module_is_rn131():
            self._fast_server_apply_reply(response)
        # A manually-sent ESSe<p>! changes the Envision state, but its reply
        # carries no status — so re-read ESGe! rather than leave the panel
        # showing what was true before the command.
        elif cmd.strip().startswith("ESSe") and not self._module_is_rn131():
            if cmd.strip() in ("ESSe0!", "ESSe1!"):
                # 0/1 start-stop Envision, which reboots the WiFi module. The
                # read-back often lands mid-reboot and comes back empty; say so
                # rather than let "Unknown" look like a failure.
                self.response_box.append(
                    "Envision start/stop reboots the WiFi module — if the status "
                    "reads Unknown, wait a few seconds and run Get Configuration.")
            self._fast_server_refresh(
                (lambda c: self._serial_send_command(c, timeout=5.0))
                if conn_type == "Serial" else (lambda c: self._wifi_send_command(c)))

    def scroll_response_to_bottom(self):
        self.response_box.moveCursor(QTextCursor.MoveOperation.End)

    # ---- Fast Server (WiFi fast-server boot) ---------------------------------
    def _fast_server_reset(self):
        """Neutral state shown before any Get Configuration has run."""
        self._fast_server_state = None
        self._fast_server_available = False
        self.fast_server_status_label.setText("— (run Get Configuration)")
        self.fast_server_checkbox.setText("Boot into Fast Server")
        self.fast_server_checkbox.setChecked(False)
        self.fast_server_checkbox.setEnabled(False)
        self.fast_server_hint.setText("")
        self.fast_server_hint.setVisible(False)

    def _fast_server_apply_state(self, able, boot, status_text, hint=""):
        """Drive the Fast Server widgets from the two ESGe! bits:
        `able` (bit 0 = Fast Server / Envision installed) enables the checkbox;
        `boot` (bit 1 = boot into Fast Server) sets its checked state. The boot
        flag is shown even when not able, so a 'boot set but not installed'
        device state reads honestly (checkbox checked but greyed)."""
        self._fast_server_available = bool(able)
        self.fast_server_status_label.setText(status_text)
        self.fast_server_checkbox.setEnabled(bool(able))
        self.fast_server_checkbox.setChecked(bool(boot))
        self.fast_server_checkbox.setText(
            "Boot into Fast Server" if able else "Boot into Fast Server — unavailable")
        self.fast_server_hint.setText(hint)
        self.fast_server_hint.setVisible(bool(hint))

    def _parse_esge(self, reply):
        """Return the ESGe! status value as a 3-bit int (0-7), or None.
        bit 0 = Envision capable (able); bit 1 = Envision boot flag;
        bit 2 = Envision currently on."""
        if not reply:
            return None
        r = reply.strip()
        if r.startswith("ESGe"):
            r = r[4:]
        if r.endswith("!"):
            r = r[:-1]
        r = r.strip()
        return int(r) if r in ("0", "1", "2", "3", "4", "5", "6", "7") else None

    def _fast_server_status_text(self, able, boot, on):
        """Human-readable Fast Server status from the three ESGe! bits."""
        if not able:
            return ("Not installed (boot flag set): update your WiFi firmware."
                    if boot else "Not installed: update your WiFi firmware.")
        if on and boot:
            return "Enabled — running now."
        if on and not boot:
            return "Running now (boot off)."
        if boot:
            return "Enabled."
        return "Available."

    def _fast_server_refresh(self, send):
        """Query ESGe! and update the status/checkbox. `send` is a callable
        taking a command string and returning the device reply. Call this after
        the ESGi parse so self._wifi_type is set.

        ESGe! returns a 3-bit field: bit 0 = Envision capable, bit 1 = Envision
        boot flag (the checkbox), bit 2 = Envision currently on. Codes 4 and 6
        (on without capable) are impossible and treated as unknown."""
        if self._module_is_rn131():
            self._fast_server_apply_state(False, False, "Not available on RN-131.")
            self.response_box.append("Fast Server: not supported on RN-131 modules.")
            self.scroll_response_to_bottom()
            return
        try:
            reply = send("ESGe!")
        except Exception as e:
            self._fast_server_apply_state(False, False, "Unknown (no response).")
            self.response_box.append(f"Fast Server query failed: {e}")
            self.scroll_response_to_bottom()
            return
        self.response_box.append(f"Sent: ESGe!\nReceived: {reply}")
        self._fast_server_apply_reply(reply)
        self.scroll_response_to_bottom()

    def _fast_server_apply_reply(self, reply):
        """Drive the Fast Server status/checkbox from an ESGe! reply — shared by
        Get Configuration and a manually-sent ESGe! in the console, so a valid
        value typed by hand is reflected in the display too.

        ESGe! returns a 3-bit field: bit 0 = capable, bit 1 = boot flag (the
        checkbox), bit 2 = currently on. Codes 4 and 6 (on without capable) are
        impossible and shown as unknown. Returns True if it was a valid value."""
        state = self._parse_esge(reply)
        self._fast_server_state = state
        if state is None:
            self._fast_server_apply_state(False, False, "Unknown status.")
            return False
        able = bool(state & 1)
        boot = bool(state & 2)
        on = bool(state & 4)
        if on and not able:
            # Impossible per firmware contract (codes 4 and 6): can't run a mode
            # the module isn't capable of. Don't trust it — show unknown/disabled.
            self.response_box.append(f"Fast Server: unexpected status code {state}.")
            self._fast_server_apply_state(False, boot, "Unknown status.", hint="")
        else:
            status = self._fast_server_status_text(able, boot, on)
            hint = "" if able else "Update your WiFi firmware."
            self._fast_server_apply_state(able, boot, status, hint=hint)
        return True

    def _fast_server_apply(self, send):
        """Push the Boot-into-Fast-Server choice after the ESSi save:
        ESSe3! = boot on, ESSe4! = boot off. A bare 'ESSe!' reply means the
        firmware does not support the option. Skipped when unavailable."""
        if not self._fast_server_available:
            return  # RN131, not installed, or no Get Configuration yet
        want_on = self.fast_server_checkbox.isChecked()
        cmd = "ESSe3!" if want_on else "ESSe4!"
        try:
            reply = send(cmd)
        except Exception as e:
            self.response_box.append(f"Fast Server set failed: {e}")
            self.scroll_response_to_bottom()
            return
        self.response_box.append(f"Sent: {cmd}\nReceived: {reply}")
        if reply and reply.strip() == "ESSe!":
            self._fast_server_apply_state(False, False,
                "Not available: update your WiFi firmware.",
                hint="Update your WiFi firmware.")
            self.response_box.append("Fast Server boot option not available on this firmware.")
        else:
            # Boot flag (bit 1) changed; the "currently on" bit (2) is unaffected
            # by setting the boot flag, so preserve it from the last ESGe! read.
            on = bool((self._fast_server_state or 0) & 4)
            self._fast_server_state = ((self._fast_server_state or 0) & ~2) | (2 if want_on else 0)
            self.fast_server_status_label.setText(
                self._fast_server_status_text(True, want_on, on))
            self.response_box.append(f"Boot into Fast Server: {'ON' if want_on else 'OFF'}.")
        self.scroll_response_to_bottom()

    def get_configuration(self):
        self.response_box.append("Get Config....")
        conn_type = self.connection_type_combo.currentText()
        if conn_type == "Serial":
            if self.serial_port and self.serial_port.is_open:
                response = self._serial_send_command("ESGi!", timeout=5.0)
            
                if not response:
                    #self.response_box.append("Connection failed, check PMC-Eight COM port selection")
                    self.response_box.append(f"No serial response from {self.serial_port.port}. On macOS select a /dev/cu.* port, not /dev/tty.*.")
                    self.scroll_response_to_bottom()
                    return
            
                self.response_box.append(f"Sent: ESGi!\nReceived: {response}")
                self.scroll_response_to_bottom()
                config = self.parse_ESGi_response(response)
                self.update_config_display(config)
                self._wifi_type = config.get("WiFi Type")
                self.save_config_button.setEnabled(True)
            
                # Issue ESGv! for firmware version.
                fw_response = self._serial_send_command("ESGv!", timeout=5.0)
            
                if not fw_response:
                    self.response_box.append("No reply received for ESGv! (timeout)")
                    self.scroll_response_to_bottom()
                    return
            
                if fw_response.startswith("ESGv"):
                    fw = fw_response[4:]
                else:
                    fw = fw_response
                if fw.endswith("!"):
                    fw = fw[:-1]
                row = self.config_grid.rowCount()
                fw_label = QLabel("FIRMWARE VERSION:")
                fw_value = QLabel(fw)
                fw_value.setMinimumWidth(360)
                self.config_grid.addWidget(fw_label, row, 0)
                self.config_grid.addWidget(fw_value, row, 1, 1, 3)
                self.response_box.append(f"Firmware Version: {fw}")
                self.scroll_response_to_bottom()
                self._fast_server_refresh(lambda c: self._serial_send_command(c, timeout=5.0))
            else:
                self.response_box.append("Serial port not connected.")
                self.scroll_response_to_bottom()
        else:
            if self.connection_socket:
                try:
                    response = self._wifi_send_command("ESGi!")
                    self.response_box.append(f"Sent: ESGi!\nReceived: {response}")
                    self.scroll_response_to_bottom()
                    config = self.parse_ESGi_response(response)
                    self.update_config_display(config)                    
                    self.scroll_response_to_bottom()

                    self._wifi_type = config.get("WiFi Type")
                    self.save_config_button.setEnabled(True)
                    fw_response = self._wifi_send_command("ESGv!")
                    if fw_response:  # firmware version is optional — skip if the mount didn't answer
                        if fw_response.startswith("ESGv"):
                            fw = fw_response[4:]
                        else:
                            fw = fw_response
                        if fw.endswith("!"):
                            fw = fw[:-1]
                        row = self.config_grid.rowCount()
                        fw_label = QLabel("FIRMWARE VERSION:")
                        fw_value = QLabel(fw)
                        fw_value.setMinimumWidth(360)
                        self.config_grid.addWidget(fw_label, row, 0)
                        self.config_grid.addWidget(fw_value, row, 1, 1, 3)
                        self.response_box.append(f"Firmware Version: {fw}")
                        self.scroll_response_to_bottom()
                    self._fast_server_refresh(lambda c: self._wifi_send_command(c))
                except Exception as e:
                    self.response_box.append(f"Error in WiFi get configuration: {e}")
                    self.scroll_response_to_bottom()
            else:
                self.response_box.append("WiFi connection not established.")
                self.scroll_response_to_bottom()

    def save_configuration(self):
        conn_type = self.connection_type_combo.currentText()
        if conn_type == "Serial":
            if self.serial_port and self.serial_port.is_open:
                cmd = self.build_config_command()
                if not cmd:
                    return
                response = self._serial_send_command(cmd)
                self.response_box.append(f"Sent: {cmd}\nReceived: {response}")
                self.scroll_response_to_bottom()
                self._fast_server_apply(lambda c: self._serial_send_command(c, timeout=5.0))
            else:
                self.response_box.append("Serial port not connected.")
                self.scroll_response_to_bottom()
        else:
            if self.connection_socket:
                try:
                    cmd = self.build_config_command()
                    if not cmd:
                        return
                    response = self._wifi_send_command(cmd)
                    self.response_box.append(f"Sent: {cmd}\nReceived: {response}")
                    self.scroll_response_to_bottom()
                    self._fast_server_apply(lambda c: self._wifi_send_command(c))
                except Exception as e:
                    self.response_box.append(f"Error in WiFi save configuration: {e}")
                    self.scroll_response_to_bottom()
            else:
                self.response_box.append("WiFi connection not established.")
                self.scroll_response_to_bottom()

    def boot_pmc8(self):
        conn_type = self.connection_type_combo.currentText()
        if conn_type == "Serial":
            if self.serial_port and self.serial_port.is_open:
                response = self._serial_send_command("ESB!")
                self.response_box.append(f"Sent: ESB!\nReceived: {response}")
                self.scroll_response_to_bottom()
            else:
                self.response_box.append("Serial port not connected.")
                self.scroll_response_to_bottom()
        else:
            if self.connection_socket:
                try:
                    response = self._wifi_send_command("ESB!")
                    self.response_box.append(f"Sent: ESB!\nReceived: {response}")
                    self.scroll_response_to_bottom()
                except Exception as e:
                    self.response_box.append(f"Error in WiFi boot PMC8: {e}")
                    self.scroll_response_to_bottom()
            else:
                self.response_box.append("WiFi connection not established.")
                self.scroll_response_to_bottom()

    def parse_ESGi_response(self, response):
        if response.startswith("ESGi"):
            data = response[4:]
        else:
            data = response
        if data.endswith("!"):
            data = data[:-1]
        if len(data) != 31:
            self.response_box.append("Unexpected ESGi! response length.")
            self.scroll_response_to_bottom()
            return {}
        baud_rate    = data[0:6]
        ip_proto_raw = data[6]
        cont_track_raw = data[7]
        run_on_boot_raw = data[8]
        hemisphere_raw = data[9]
        sr_fraction_ra = data[10:13]
        sr_fraction_dec = data[13:16]
        mount_raw    = data[16:18]
        motor_current_slew = data[18:22]
        motor_current_track = data[22:26]
        wifi_channel = data[26:28]
        st4_disable_raw = data[28]
        st4_type_raw = data[29]
        wifi_type_raw = data[30]

        ip_proto = "TCP" if ip_proto_raw == "0" else "UDP"
        cont_track = "On" if cont_track_raw == "1" else "Off"
        run_on_boot = "YES" if run_on_boot_raw == "1" else "NO"
        hemisphere = "North" if hemisphere_raw == "1" else "South"
        try:
            mount_int = int(mount_raw)
        except ValueError:
            mount_int = -1
        if mount_int in [8, 9, 10, 11]:
            mount = "Exos2"
        elif mount_int in [4, 5, 6, 7]:
            mount = "ES G11"
        elif mount_int in [0, 1]:
            mount = "iexos100"
        elif mount_int == 2:
            mount = "iexos200"
        elif mount_int == 3:
            mount = "iexos300"
        elif mount_int == 13:
            mount = "Titan"
        elif mount_int == 15:
            mount = "ASKO"
        elif mount_int == 14:
            mount = "MSRO"
        elif mount_int == 12:
            mount = "Scotty"
        else:
            mount = "Unknown"
        st4_disable = "Enabled" if st4_disable_raw == "0" else "Disabled"
        st4_type = "Analog" if st4_type_raw == "1" else "Digital"
        if wifi_type_raw == "0":
            wifi_type = "RN131"
        elif wifi_type_raw == "1":
            wifi_type = "8266"
        elif wifi_type_raw == "2":
            wifi_type = "ESP32"
        else:
            wifi_type = "Unknown"

        config = {
            "Baud Rate": baud_rate,
            "IP Protocol": ip_proto,
            "Continuous Track": cont_track,
            "Run on Boot": run_on_boot,
            "Hemisphere": hemisphere,
            "Sidereal Rate Fraction RA %": sr_fraction_ra,
            "Sidereal Rate Fraction DEC %": sr_fraction_dec,
            "Mount Type": mount,
            "Motor Current Slew, ma": motor_current_slew,
            "Motor Current Track, ma": motor_current_track,
            "WiFi Channel": wifi_channel,
            "ST4 Status": st4_disable,
            "ST4 Type": st4_type,
            "WiFi Type": wifi_type,
        }
        return config




    def update_config_display(self, config):
        while self.config_grid.count():
            child = self.config_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.config_widgets = {}
        field_widths = {
            "Sidereal Rate Fraction RA %": 72,
            "Sidereal Rate Fraction DEC %": 72,
            "Motor Current Slew, ma": 88,
            "Motor Current Track, ma": 88,
            "WiFi Channel": 64,
        }
        dropdown_widths = {
            "ST4 Status": 118,
            "IP Protocol": 92,
            "Continuous Track": 96,
            "Run on Boot": 92,
            "Hemisphere": 104,
            "Mount Type": 132,
        }
        label_widths = {
            "ST4 Type": 96,
            "WiFi Type": 96,
            "Baud Rate": 110,
        }
        dropdown_fields = {
            "IP Protocol": [("TCP", "0"), ("UDP", "1")],
            "Continuous Track": [("On", "1"), ("Off", "0")],
            "Run on Boot": [("YES", "1"), ("NO", "0")],
            "Hemisphere": [("North", "1"), ("South", "0")],
            "Mount Type": [("Exos2", "Exos2"), ("ES G11", "ES G11"), ("iexos100", "iexos100"),
                           ("iexos200", "iexos200"), ("iexos300", "iexos300"), ("Titan", "Titan"),
                           ("ASKO", "ASKO"), ("MSRO", "MSRO"), ("Scotty", "Scotty"), ("Unknown", "99")],
            "ST4 Status": [("Enabled", "0"), ("Disabled", "1")],
        }
        label_fields = ["ST4 Type", "WiFi Type", "Baud Rate"]
        items = list(config.items())
        half = (len(items) + 1) // 2
        for i, (key, value) in enumerate(items):
            if key in dropdown_fields:
                widget = QComboBox()
                for disp, internal in dropdown_fields[key]:
                    widget.addItem(disp, internal)
                idx = widget.findText(value)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                widget.setFixedWidth(dropdown_widths.get(key, 110))
            elif key in label_fields:
                widget = QLabel(value)
                widget.setMinimumWidth(label_widths.get(key, 110))
            else:
                widget = QLineEdit(value)
                if key in field_widths:
                    widget.setFixedWidth(field_widths[key])
            if i < half:
                self.config_grid.addWidget(QLabel(key + ":"), i, 0)
                self.config_grid.addWidget(widget, i, 1)
            else:
                self.config_grid.addWidget(QLabel(key + ":"), i - half, 2)
                self.config_grid.addWidget(widget, i - half, 3)
            self.config_widgets[key] = widget
        self.config_populated = True
        self.update_command_dropdown()
        # Reflect the module type detected here in the Network tab's WiFi-module
        # dropdown, so the user doesn't have to select it by hand.
        self._sync_net_module_from_config(config.get("WiFi Type"))

    def _sync_net_module_from_config(self, wifi_type):
        """Pre-set the Network tab's WiFi-module dropdown from the type detected
        by Get Configuration (ESGi! byte 30). The config value '8266' maps to the
        dropdown's 'ESP8266' label; RN131/ESP32 match directly. Unknown/blank
        leaves the current selection alone."""
        target = {"RN131": "RN131", "8266": "ESP8266", "ESP32": "ESP32"}.get(wifi_type)
        combo = getattr(self, "net_module_combo", None)
        if target and combo is not None:
            idx = combo.findText(target)
            if idx >= 0 and combo.currentIndex() != idx:
                combo.setCurrentIndex(idx)

    def build_config_command(self):
        mount_mapping = {
            "Exos2": "08",
            "ES G11": "04",
            "iexos100": "00",
            "iexos200": "02",
            "iexos300": "03",
            "Titan": "13",
            "ASKO": "15",
            "MSRO": "14",
            "Scotty": "12",
            "Unknown": "99"
        }
        st4_type_mapping = {"ANALOG": "1", "DIGITAL": "0"}
        wifi_type_mapping = {"RN131": "0", "8266": "1", "ESP32": "2"}
        try:
            baud_rate = self.config_widgets["Baud Rate"].text().strip()
            baud_rate = f"{int(baud_rate):06d}"
            ip_proto = self.config_widgets["IP Protocol"].currentData()
            cont_track = self.config_widgets["Continuous Track"].currentData()
            run_on_boot = self.config_widgets["Run on Boot"].currentData()
            hemisphere = self.config_widgets["Hemisphere"].currentData()
            srf_ra = self.config_widgets["Sidereal Rate Fraction RA %"].text().strip()
            srf_ra = f"{int(srf_ra):03d}"
            srf_dec = self.config_widgets["Sidereal Rate Fraction DEC %"].text().strip()
            srf_dec = f"{int(srf_dec):03d}"
            mount_text = self.config_widgets["Mount Type"].currentText()
            mount = mount_mapping.get(mount_text, "99")
            mc_slew = self.config_widgets["Motor Current Slew, ma"].text().strip()
            mc_slew = f"{int(mc_slew):04d}"
            mc_track = self.config_widgets["Motor Current Track, ma"].text().strip()
            mc_track = f"{int(mc_track):04d}"
            wifi_chan = self.config_widgets["WiFi Channel"].text().strip()
            wifi_chan = f"{int(wifi_chan):02d}"
            st4_status = self.config_widgets["ST4 Status"].currentData()
            st4_type_text = self.config_widgets["ST4 Type"].text().strip().upper()
            st4_type = st4_type_mapping.get(st4_type_text, "0")
            wifi_type_text = self.config_widgets["WiFi Type"].text().strip().upper()
            wifi_type = wifi_type_mapping.get(wifi_type_text, "0")
            cmd = "ESSi"
            cmd += baud_rate
            cmd += ip_proto
            cmd += cont_track
            cmd += run_on_boot
            cmd += hemisphere
            cmd += srf_ra
            cmd += srf_dec
            if mount.isdigit():
                cmd += f"{int(mount):02d}"
            else:
                cmd += mount
            cmd += mc_slew
            cmd += mc_track
            cmd += wifi_chan
            cmd += st4_status
            cmd += st4_type
            cmd += wifi_type
            cmd += "!"
            self.response_box.append(f"Built Config Command: {cmd}")
            self.scroll_response_to_bottom()
            return cmd
        except Exception as e:
            self.response_box.append(f"Error building config command: {e}")
            self.scroll_response_to_bottom()
            return None

    def _raw_serial_query(self, sp, cmd, timeout=3.0):
        """Send `cmd` on an already-open pyserial port and return the first
        ES...! reply that isn't the command echo (empty string if none)."""
        orig = sp.timeout
        try:
            sp.timeout = 0.1
            try:
                sp.reset_input_buffer()
            except Exception:
                pass
            sp.write((cmd + "\r\n").encode("ascii"))
            sp.flush()
            echo = cmd.strip()
            deadline = time.time() + timeout
            frame = bytearray()
            while time.time() < deadline:
                b = sp.read(1)
                if not b:
                    continue
                frame.extend(b)
                if b not in (b"!", b"\n"):
                    continue
                text = bytes(frame).decode("ascii", errors="replace").strip().strip("\r\n")
                i = text.find("ES")
                if i > 0:
                    text = text[i:]
                if text and text != echo:
                    return text
                frame.clear()
            return ""
        finally:
            sp.timeout = orig

    def _raw_serial_command(self, sp, cmd):
        """Fire a command on an open pyserial port without waiting for a reply."""
        try:
            sp.reset_input_buffer()
        except Exception:
            pass
        sp.write((cmd + "\r\n").encode("ascii"))
        sp.flush()

    def _wait_with_countdown(self, seconds, label):
        """Block for `seconds` while keeping the GUI responsive, showing the
        countdown on the upload status label next to the button."""
        self.response_box.append(f"{label}…")
        self.scroll_response_to_bottom()
        end = time.time() + seconds
        last = None
        while True:
            remaining = end - time.time()
            if remaining <= 0:
                break
            r = int(remaining) + 1
            if r != last:
                self.upload_status_label.setText(f"{label} — {r}s")
                last = r
            QApplication.processEvents()
            time.sleep(0.05)
        self.upload_status_label.setText("")
        self.response_box.append(f"{label} done.")
        self.scroll_response_to_bottom()

    def _ensure_envision_off_for_upload(self, port):
        """Before a Propeller download, stop Envision (Fast Server) mode if it
        is running. While active it holds the serial line and corrupts the
        upload (checksum NAK). Query ESGe!; if the 'currently on' bit is set
        (reply value >= 4) send ESSe0! and wait ~5 s for the WiFi module to
        reboot. Uses the live serial connection if present, else a temp one.
        Returns True if it stopped Envision (module rebooted), else False."""
        if self._module_is_rn131():
            return False  # RN131 has no Fast Server/Envision — nothing to stop
        owns_temp = False
        if self.serial_port is not None and self.serial_port.is_open:
            sp = self.serial_port
        else:
            try:
                sp = serial.Serial()
                sp.port = port
                sp.baudrate = 115200
                sp.timeout = 1
                sp.write_timeout = 1
                sp.dtr = False
                sp.rts = False
                sp.open()
                owns_temp = True
            except Exception as e:
                self.response_box.append(f"Envision pre-check skipped (could not open {port}: {e})")
                self.scroll_response_to_bottom()
                return False

        need_reset = False
        try:
            reply = self._raw_serial_query(sp, "ESGe!", timeout=3.0)
            self.response_box.append(
                f"Pre-program check — Sent: ESGe!  Received: {reply or '(no reply)'}")
            state = self._parse_esge(reply)
            if state is not None and state >= 4:
                need_reset = True
                self.upload_status_label.setText("WiFi module rebooting…")
                QApplication.processEvents()
                self.response_box.append(
                    "Envision (Fast Server) mode is ACTIVE — stopping it before "
                    "programming (ESSe0!). The WiFi module will now reboot; please wait.")
                self.scroll_response_to_bottom()
                self._raw_serial_command(sp, "ESSe0!")
            else:
                self.response_box.append("Envision mode not active — OK to program.")
            self.scroll_response_to_bottom()
        except Exception as e:
            self.response_box.append(f"Envision pre-check error: {e}")
            self.scroll_response_to_bottom()
        finally:
            # Release the serial line so the module can reboot cleanly and the
            # loader can open the port.
            if owns_temp:
                try:
                    sp.close()
                except Exception:
                    pass
            elif need_reset:
                self.disconnect_serial()

        if need_reset:
            self._wait_with_countdown(5, "WiFi module rebooting")
        return need_reset

    def _reconnect_to_port(self, port):
        """Reconnect serial to a specific port — never to whatever the combo
        happens to show. Refreshes the list first so a re-enumerated device is
        picked up; if that exact port is gone, ask the user to reselect."""
        self.refresh_ports()
        idx = self.port_combo.findData(port)
        if idx >= 0:
            self.port_combo.setCurrentIndex(idx)
            self.response_box.append(f"Reconnecting to {port} after upload...")
            self.scroll_response_to_bottom()
            self.connect_serial()
        else:
            self.response_box.append(
                f"Upload done. {port} is no longer listed — select the PMC-Eight "
                f"COM port to reconnect.")
            self.scroll_response_to_bottom()

    def open_upload_dialog(self):
        selected_port = (self.port_combo.currentData() or "").strip()
        if not selected_port:
            self.response_box.append("No serial port specified, please select before programming")
            self.scroll_response_to_bottom()
            return

        was_connected = self.serial_port is not None and self.serial_port.is_open

        # Stop Envision (Fast Server) mode if it is running — it holds the serial
        # line and corrupts the download. May reboot the WiFi module.
        did_reset = self._ensure_envision_off_for_upload(selected_port)

        # A module reboot can re-enumerate the COM port; make sure the port we
        # are about to program is the one actually present now.
        if did_reset:
            self.refresh_ports()
            if self.port_combo.findData(selected_port) < 0:
                self.upload_status_label.setText("")
                self.response_box.append(
                    f"Envision stopped, but {selected_port} is no longer listed "
                    f"(the module re-enumerated). Select the PMC-Eight COM port and "
                    f"press Upload again — Envision is already off now.")
                self.scroll_response_to_bottom()
                return
            self.port_combo.setCurrentIndex(self.port_combo.findData(selected_port))

        reconnect = False
        # If still connected, disconnect for the upload.
        if self.serial_port is not None and self.serial_port.is_open:
            self.response_box.append("Disconnecting current serial connection for upload...")
            self.scroll_response_to_bottom()
            reconnect = True
            self.disconnect_serial()
        elif was_connected:
            # The Envision reset already dropped the live link; still reconnect
            # after the upload finishes.
            reconnect = True

        # Open the uploader dialog, passing the selected port
        dialog = UploadDialog(self, serial_port=selected_port)
        dialog.exec()

        # After the uploader finishes, reconnect to the SAME port if needed.
        self.upload_status_label.setText("")
        if reconnect:
            self._reconnect_to_port(selected_port)










if __name__ == '__main__':
    if not preflight_assets():
        sys.exit(1)

    # Raspberry Pi OS (Bookworm) defaults to Wayland, but python3-pyqt6 doesn't
    # ship the Qt Wayland platform plugin — Qt prints "Could not find the Qt
    # platform plugin 'wayland'" and falls back on its own. Pin the well-tested
    # X11/XWayland plugin (xcb) here, before Qt initialises, so it applies no
    # matter how the app was launched (launcher, desktop icon, or python3
    # directly). Linux only; setdefault honours an explicit QT_QPA_PLATFORM.
    if sys.platform.startswith("linux"):
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

    try:
        app = QApplication(sys.argv)
        # Pin the Fusion style so widgets render identically across every Windows
        # version / Qt build. The native "windowsvista" style paints QTabBar (and
        # other sub-controls) inconsistently under a global QWidget QSS rule, which
        # is what made the Network tab render blank for some users in v0.2.0.
        app.setStyle("Fusion")
        window = PMC8Configurator()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print("Error during application startup:", e)


