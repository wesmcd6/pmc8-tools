import sys
import socket
import serial
import serial.tools.list_ports
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QComboBox, QTextEdit, QFormLayout, QLineEdit, QHBoxLayout, QGridLayout, QSpacerItem, QSizePolicy
)
from PyQt6.QtGui import QTextCursor

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
    "ESSi!": {
        "desc": "Set PMC8 Configuration settings (computed from fields)",
        "template": "",  # Built dynamically.
        "params": []
    }
}

class PMC8Configurator(QWidget):
    def __init__(self):
        super().__init__()
        self.param_widgets = {}      # For command parameters.
        self.config_widgets = {}     # For configuration display.
        self.config_populated = False
        self.connection_socket = None  # For WiFi connections.
        self.serial_port = None      # For serial connections.
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()

        # Connection Type Section:
        conn_layout = QHBoxLayout()
        conn_label = QLabel("Connection Type:")
        conn_layout.addWidget(conn_label)
        self.connection_type_combo = QComboBox()
        self.connection_type_combo.addItems(["Serial", "WiFi"])
        self.connection_type_combo.currentIndexChanged.connect(self.update_connection_ui)
        conn_layout.addWidget(self.connection_type_combo)
        main_layout.addLayout(conn_layout)

        # Serial / WiFi Settings Section:
        self.conn_settings_layout = QHBoxLayout()
        # Serial port:
        self.port_combo = QComboBox()
        self.refresh_ports()
        self.conn_settings_layout.addWidget(QLabel("Serial Port:"))
        self.conn_settings_layout.addWidget(self.port_combo)
        # WiFi settings:
 
        self.port_edit = QLineEdit()
        self.port_edit.setPlaceholderText("Port")
        self.port_edit.setText("54372")    # Set constant port
        self.port_edit.setReadOnly(True)   # Make it uneditable



        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("IP Address")
#        self.port_edit = QLineEdit()
#        self.port_edit.setPlaceholderText("Port")
 

        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["TCP", "UDP"])
        self.ip_edit.hide()
        self.port_edit.hide()
        self.protocol_combo.hide()
        self.conn_settings_layout.addWidget(QLabel("IP Address:"))
        self.conn_settings_layout.addWidget(self.ip_edit)
        self.conn_settings_layout.addWidget(QLabel("Port:"))
        self.conn_settings_layout.addWidget(self.port_edit)
        self.conn_settings_layout.addWidget(QLabel("Protocol:"))
        self.conn_settings_layout.addWidget(self.protocol_combo)
        main_layout.addLayout(self.conn_settings_layout)

        # Connect / Disconnect Buttons:
        btn_layout = QHBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_device)
        btn_layout.addWidget(self.connect_button)
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_device)
        btn_layout.addWidget(self.disconnect_button)
        main_layout.addLayout(btn_layout)

        # Function Buttons (GET CONFIGURATION, SAVE CONFIGURATION, BOOT PMC8):
        func_layout = QHBoxLayout()
        func_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        self.get_config_button = QPushButton("GET CONFIGURATION")
        self.get_config_button.clicked.connect(self.get_configuration)
        func_layout.addWidget(self.get_config_button)
        self.save_config_button = QPushButton("SAVE CONFIGURATION")
        self.save_config_button.clicked.connect(self.save_configuration)
        self.save_config_button.setEnabled(False)
        func_layout.addWidget(self.save_config_button)
        self.boot_pmc8_button = QPushButton("BOOT PMC8")
        self.boot_pmc8_button.clicked.connect(self.boot_pmc8)
        func_layout.addWidget(self.boot_pmc8_button)
        func_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        main_layout.addLayout(func_layout)

        # Command Selection Section.
        self.command_label = QLabel("Select Command:")
        main_layout.addWidget(self.command_label)
        self.command_combo = QComboBox()
        self.update_command_dropdown()  # Method defined below.
        self.command_combo.currentIndexChanged.connect(self.update_command_description)
        self.command_combo.currentIndexChanged.connect(lambda: self.update_param_fields(self.command_combo.currentData()))
        main_layout.addWidget(self.command_combo)
        self.command_desc_label = QLabel("Command Description:")
        main_layout.addWidget(self.command_desc_label)
        if self.command_combo.count() > 0:
            initial_key = self.command_combo.itemData(0)
            self.command_desc_label.setText(f"Description: {COMMANDS[initial_key]['desc']}")

        # Parameter Input Area.
        self.param_area = QWidget()
        self.param_layout = QFormLayout()
        self.param_area.setLayout(self.param_layout)
        main_layout.addWidget(self.param_area)

        # Send Command Button.
        self.send_button = QPushButton("Send Command")
        self.send_button.clicked.connect(self.send_command)
        main_layout.addWidget(self.send_button)

        # Response Display.
        self.response_label = QLabel("Response:")
        main_layout.addWidget(self.response_label)
        self.response_box = QTextEdit()
        self.response_box.setReadOnly(True)
        main_layout.addWidget(self.response_box)

        # Configuration Settings Display.
        self.config_area_label = QLabel("Configuration Settings:")
        main_layout.addWidget(self.config_area_label)
        self.config_grid = QGridLayout()  # Two-column layout.
        self.config_widget = QWidget()
        self.config_widget.setLayout(self.config_grid)
        main_layout.addWidget(self.config_widget)

        # Refresh Ports Button.
        self.refresh_button = QPushButton("Refresh Ports")
        self.refresh_button.clicked.connect(self.refresh_ports)
        main_layout.addWidget(self.refresh_button)

        self.setLayout(main_layout)
        self.setWindowTitle("PMC-Eight Configurator")
        self.resize(600, 700)
        self.update_param_fields(self.command_combo.currentData())
        self.update_connection_ui()

    def update_connection_ui(self):
        conn_type = self.connection_type_combo.currentText()
        if conn_type == "Serial":
            self.port_combo.show()
            self.ip_edit.hide()
            self.port_edit.hide()
            self.protocol_combo.hide()
        else:
            self.port_combo.hide()
            self.ip_edit.show()
            self.port_edit.show()
            self.protocol_combo.show()

    def refresh_ports(self):
        try:
            self.port_combo.clear()
            for port in serial.tools.list_ports.comports():
                self.port_combo.addItem(port.device)
        except Exception as e:
            print(f"Error refreshing ports: {e}")

    def connect_device(self):
        conn_type = self.connection_type_combo.currentText()
        if conn_type == "Serial":
            self.connect_serial()
        else:
            self.connect_wifi()

    def disconnect_device(self):
        conn_type = self.connection_type_combo.currentText()
        if conn_type == "Serial":
            self.disconnect_serial()
        else:
            self.disconnect_wifi()

    def connect_serial(self):
        port = self.port_combo.currentText().strip()
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
            self.serial_port.dtr = False
            self.serial_port.rts = False
            self.serial_port.open()
            self.response_box.append(f"Connected to {port} (Serial, DTR/RTS held low)")
        except Exception as e:
            self.response_box.append(f"Failed to connect (Serial): {e}")
        finally:
            self.scroll_response_to_bottom()

    def disconnect_serial(self):
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
                self.response_box.append("Serial port disconnected.")
                self.serial_port = None
        except Exception as e:
            self.response_box.append(f"Error disconnecting (Serial): {e}")
        finally:
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
                self.connection_socket.connect((ip, port))
            else:
                self.connection_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.connection_socket.connect((ip, port))
            self.response_box.append(f"Connected to {ip}:{port} ({proto})")
        except Exception as e:
            self.response_box.append(f"Failed to connect (WiFi): {e}")
        finally:
            self.scroll_response_to_bottom()

    def disconnect_wifi(self):
        try:
            if self.connection_socket:
                self.connection_socket.close()
                self.response_box.append("WiFi connection disconnected.")
                self.connection_socket = None
        except Exception as e:
            self.response_box.append(f"Error disconnecting (WiFi): {e}")
        finally:
            self.scroll_response_to_bottom()

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

    def send_command(self):
        conn_type = self.connection_type_combo.currentText()
        if conn_type == "Serial":
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.reset_input_buffer()
                command_key = self.command_combo.currentData()
                if command_key == "ESSi!":
                    cmd = self.build_config_command()
                    if not cmd:
                        return
                    self.serial_port.write((cmd + "\r\n").encode())
                    self.serial_port.flush()
                    response = self.serial_port.readline().decode().strip()
                    self.serial_port.reset_input_buffer()
                    self.response_box.append(f"Sent: {cmd}\nReceived: {response}")
                    self.scroll_response_to_bottom()
                else:
                    command_info = COMMANDS.get(command_key, {})
                    template = command_info.get("template", "")
                    params = {}
                    for param in command_info.get("params", []):
                        param_name = param["name"]
                        param_value = self.param_widgets[param_name].text().strip()
                        if not param_value:
                            self.response_box.append(f"Parameter '{param_name}' is required.")
                            self.scroll_response_to_bottom()
                            return
                        params[param_name] = param_value
                    try:
                        command_to_send = template.format(**params)
                    except KeyError as e:
                        self.response_box.append(f"Missing parameter: {e}")
                        self.scroll_response_to_bottom()
                        return
                    self.serial_port.write((command_to_send + "\r\n").encode())
                    self.serial_port.flush()
                    response = self.serial_port.readline().decode().strip()
                    self.serial_port.reset_input_buffer()
                    self.response_box.append(f"Sent: {command_to_send}\nReceived: {response}")
                    self.scroll_response_to_bottom()
                    if command_key == "ESGi!":
                        config = self.parse_ESGi_response(response)
                        self.update_config_display(config)
                        self.save_config_button.setEnabled(True)
            else:
                self.response_box.append("Serial port not connected.")
                self.scroll_response_to_bottom()
        else:  # WiFi
            if self.connection_socket:
                command_key = self.command_combo.currentData()
                if command_key == "ESSi!":
                    cmd = self.build_config_command()
                    if not cmd:
                        return
                else:
                    command_info = COMMANDS.get(command_key, {})
                    template = command_info.get("template", "")
                    params = {}
                    for param in command_info.get("params", []):
                        param_name = param["name"]
                        param_value = self.param_widgets[param_name].text().strip()
                        if not param_value:
                            self.response_box.append(f"Parameter '{param_name}' is required.")
                            self.scroll_response_to_bottom()
                            return
                        params[param_name] = param_value
                    try:
                        cmd = template.format(**params)
                    except KeyError as e:
                        self.response_box.append(f"Missing parameter: {e}")
                        self.scroll_response_to_bottom()
                        return
                try:
                    self.connection_socket.send((cmd + "\r\n").encode())
                    response = self.connection_socket.recv(1024).decode().strip()
                    self.response_box.append(f"Sent: {cmd}\nReceived: {response}")
                    self.scroll_response_to_bottom()
                except Exception as e:
                    self.response_box.append(f"Error during send/receive (WiFi): {e}")
                self.scroll_response_to_bottom()
            else:
                self.response_box.append("WiFi connection not established.")
                self.scroll_response_to_bottom()

    def scroll_response_to_bottom(self):
        self.response_box.moveCursor(QTextCursor.MoveOperation.End)

    def get_configuration(self):
        conn_type = self.connection_type_combo.currentText()
        if conn_type == "Serial":
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.reset_input_buffer()
                self.serial_port.write(("ESGi!" + "\r\n").encode())
                self.serial_port.flush()
                response = self.serial_port.readline().decode().strip()
                self.serial_port.reset_input_buffer()
                self.response_box.append(f"Sent: ESGi!\nReceived: {response}")
                self.scroll_response_to_bottom()
                config = self.parse_ESGi_response(response)
                self.update_config_display(config)
                self.save_config_button.setEnabled(True)
                # Issue ESGv! for firmware version.
                self.serial_port.reset_input_buffer()
                self.serial_port.write(("ESGv!" + "\r\n").encode())
                self.serial_port.flush()
                fw_response = self.serial_port.readline().decode().strip()
                self.serial_port.reset_input_buffer()
                if fw_response.startswith("ESGv"):
                    fw = fw_response[4:]
                else:
                    fw = fw_response
                if fw.endswith("!"):
                    fw = fw[:-1]
                row = self.config_grid.rowCount()
                fw_label = QLabel("FIRMWARE VERSION:")
                fw_value = QLabel(fw)
                fw_value.setFixedWidth(200)
                self.config_grid.addWidget(fw_label, row, 0)
                self.config_grid.addWidget(fw_value, row, 1, 1, 3)
                self.response_box.append(f"Firmware Version: {fw}")
                self.scroll_response_to_bottom()
            else:
                self.response_box.append("Serial port not connected.")
                self.scroll_response_to_bottom()
        else:
            if self.connection_socket:
                try:
                    self.connection_socket.send(("ESGi!" + "\r\n").encode())
                    response = self.connection_socket.recv(1024).decode().strip()
                    self.response_box.append(f"Sent: ESGi!\nReceived: {response}")
                    self.scroll_response_to_bottom()
                    config = self.parse_ESGi_response(response)
                    self.update_config_display(config)                    
                    self.scroll_response_to_bottom()

                    self.save_config_button.setEnabled(True)
                    self.connection_socket.send(("ESGv!" + "\r\n").encode())
                    fw_response = self.connection_socket.recv(1024).decode().strip()
                    if fw_response.startswith("ESGv"):
                        fw = fw_response[4:]
                    else:
                        fw = fw_response
                    if fw.endswith("!"):
                        fw = fw[:-1]
                    row = self.config_grid.rowCount()
                    fw_label = QLabel("FIRMWARE VERSION:")
                    fw_value = QLabel(fw)
                    fw_value.setFixedWidth(200)
                    self.config_grid.addWidget(fw_label, row, 0)
                    self.config_grid.addWidget(fw_value, row, 1, 1, 3)
                    self.response_box.append(f"Firmware Version: {fw}")
                    self.scroll_response_to_bottom()
                    self.scroll_response_to_bottom()
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
                self.serial_port.reset_input_buffer()
                self.serial_port.write((cmd + "\r\n").encode())
                self.serial_port.flush()
                response = self.serial_port.readline().decode().strip()
                self.serial_port.reset_input_buffer()
                self.response_box.append(f"Sent: {cmd}\nReceived: {response}")
                self.scroll_response_to_bottom()
            else:
                self.response_box.append("Serial port not connected.")
                self.scroll_response_to_bottom()
        else:
            if self.connection_socket:
                try:
                    cmd = self.build_config_command()
                    if not cmd:
                        return
                    self.connection_socket.send((cmd + "\r\n").encode())
                    response = self.connection_socket.recv(1024).decode().strip()
                    self.response_box.append(f"Sent: {cmd}\nReceived: {response}")
                    self.scroll_response_to_bottom()
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
                self.serial_port.reset_input_buffer()
                self.serial_port.write(("ESB!" + "\r\n").encode())
                self.serial_port.flush()
                response = self.serial_port.readline().decode().strip()
                self.serial_port.reset_input_buffer()
                self.response_box.append(f"Sent: ESB!\nReceived: {response}")
                self.scroll_response_to_bottom()
            else:
                self.response_box.append("Serial port not connected.")
                self.scroll_response_to_bottom()
        else:
            if self.connection_socket:
                try:
                    self.connection_socket.send(("ESB!" + "\r\n").encode())
                    response = self.connection_socket.recv(1024).decode().strip()
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
        field_max_chars = {
            "Sidereal Rate Fraction RA %": 3,
            "Sidereal Rate Fraction DEC %": 3,
            "Motor Current Slew, ma": 4,
            "Motor Current Track, ma": 4,
            "WiFi Channel": 2,
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
                widget.setFixedWidth(80)
            elif key in label_fields:
                widget = QLabel(value)
                widget.setFixedWidth(80)
            else:
                widget = QLineEdit(value)
                if key in field_max_chars:
                    widget.setFixedWidth(field_max_chars[key] * 8)
            if i < half:
                self.config_grid.addWidget(QLabel(key + ":"), i, 0)
                self.config_grid.addWidget(widget, i, 1)
            else:
                self.config_grid.addWidget(QLabel(key + ":"), i - half, 2)
                self.config_grid.addWidget(widget, i - half, 3)
            self.config_widgets[key] = widget
        self.config_populated = True
        self.update_command_dropdown()
 
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



if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        window = PMC8Configurator()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print("Error during application startup:", e)

