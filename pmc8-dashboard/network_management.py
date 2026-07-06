"""
Network Management — multiplatform PMC-Eight WiFi configuration.

Mixin for PMC8Configurator (PMC8_Dashboard.py). Adds a "Network" tab that
configures the PMC-Eight WiFi module to join a home network, or restores it to
factory default — for all three module types, over the existing serial link:

  * ESP32   : ESPw42!  + AT+CWMODE=1 / AT+CWJAP / AT+CIPSTA?  (IP via CIPSTA?)
  * ESP8266 : ESPw42!  + AT+CWMODE=1 / AT+CWJAP / AT+CIFSR    (IP via CIFSR)
  * RN131   : ESPw42   + set wlan ... / save / reboot         (IP via get ip a)

Restore-to-default:
  * ESP32 / ESP8266 : nothing to do — the module reverts on the next PMC-Eight
    reboot (use BOOT PMC8 on the Configurator tab).
  * RN131 : full factory-default AP restore (192.168.47.1, SSID/passphrase
    "PMC-Eight", TCP+UDP 54372) — ported from the UFCT "Restore RN131" routine.

Framing: the PMC-Eight serial passthrough uses '@' as the AT line terminator, so
commands carry their own '@'. The mode-enter tokens (ESPw42! / ESPw42 /
ESPw42!$$$) and the passthrough-exit (###@) are sent verbatim. This mirrors the
Windows VB tools byte-for-byte; only the WinForms shell is replaced by Qt, so it
runs unchanged on Windows / macOS / Linux.

Requires a SERIAL connection (these commands go to the Propeller, which relays
them to the WiFi module — not over WiFi).
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QComboBox, QLineEdit, QPushButton, QTextEdit,
)
from PyQt6.QtGui import QTextCursor


class NetworkManagementMixin:
    """Adds the Network tab + WiFi-config flows to PMC8Configurator."""

    # ── UI ───────────────────────────────────────────────────────────
    def build_network_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(14)

        intro = QLabel(
            "Configure the PMC-Eight WiFi module to join your home network, or restore it "
            "to factory default.\nRequires a SERIAL connection — connect on the Configurator "
            "tab first (Serial, not WiFi)."
        )
        intro.setWordWrap(True)
        v.addWidget(intro)

        form = QFormLayout()
        self.net_module_combo = QComboBox()
        self.net_module_combo.addItems(["ESP32", "ESP8266", "RN131"])
        self.net_module_combo.currentIndexChanged.connect(self._net_update_ui)
        form.addRow("WiFi module:", self.net_module_combo)

        self.net_ssid_edit = QLineEdit()
        self.net_ssid_edit.setPlaceholderText("Home WiFi SSID")
        form.addRow("SSID:", self.net_ssid_edit)

        self.net_pass_edit = QLineEdit()
        self.net_pass_edit.setPlaceholderText("Home WiFi password")
        form.addRow("Password:", self.net_pass_edit)

        self.net_ip_edit = QLineEdit()
        self.net_ip_edit.setReadOnly(True)
        self.net_ip_edit.setPlaceholderText("(assigned IP appears here)")
        form.addRow("Assigned IP:", self.net_ip_edit)
        v.addLayout(form)

        btn_row = QHBoxLayout()
        self.net_config_button = QPushButton("Configure for Home Network")
        self.net_config_button.clicked.connect(self.configure_home_network)
        btn_row.addWidget(self.net_config_button)

        self.net_get_ip_button = QPushButton("Get WiFi Address")
        self.net_get_ip_button.clicked.connect(self.get_wifi_address)
        btn_row.addWidget(self.net_get_ip_button)

        self.net_restore_button = QPushButton("Restore to Default")
        self.net_restore_button.clicked.connect(self.restore_network_default)
        btn_row.addWidget(self.net_restore_button)
        v.addLayout(btn_row)

        self.net_restore_note = QLabel("")
        self.net_restore_note.setWordWrap(True)
        v.addWidget(self.net_restore_note)

        self.net_log = QTextEdit()
        self.net_log.setReadOnly(True)
        v.addWidget(self.net_log, 1)

        self._net_loading_credentials = False
        if getattr(self, "tabs", None):
            self.tabs.currentChanged.connect(self._net_handle_tab_changed)
        self._net_load_credentials()
        self.net_module_combo.currentIndexChanged.connect(self._net_save_credentials)
        self.net_ssid_edit.editingFinished.connect(self._net_save_credentials)
        self.net_pass_edit.editingFinished.connect(self._net_save_credentials)
        self._net_update_ui()
        return w

    def _net_handle_tab_changed(self, index):
        if getattr(self, "tabs", None) and self.tabs.tabText(index) == "Network":
            self._net_load_credentials()
            self._net_update_ui()

    def _net_update_ui(self):
        is_rn131 = self.net_module_combo.currentText() == "RN131"
        self.net_restore_button.setEnabled(is_rn131)
        if is_rn131:
            self.net_restore_note.setText(
                "RN131: 'Restore to Default' rewrites the module to PMC-Eight AP mode "
                "(192.168.47.1, SSID/passphrase \"PMC-Eight\", TCP+UDP on 54372)."
            )
        else:
            self.net_restore_note.setText(
                "ESP32 / ESP8266: no restore needed — the module returns to default on the next "
                "PMC-Eight reboot (use BOOT PMC8 on the Configurator tab)."
            )

    # ── helpers ──────────────────────────────────────────────────────
    def _net_credentials_path(self):
        return Path.cwd() / "pmc8_network_credentials.json"

    def _net_load_credentials(self):
        path = self._net_credentials_path()
        if not path.is_file():
            return
        try:
            self._net_loading_credentials = True
            data = json.loads(path.read_text(encoding="utf-8"))
            module = str(data.get("module", "")).strip()
            if module:
                idx = self.net_module_combo.findText(module)
                if idx >= 0:
                    self.net_module_combo.setCurrentIndex(idx)
            self.net_ssid_edit.setText(str(data.get("ssid", "")))
            self.net_pass_edit.setText(str(data.get("password", "")))
            self._net_log(f"Loaded network credentials from {path.name}.")
        except Exception as e:  # noqa: BLE001 - credentials should not block the tab
            self._net_log(f"WARNING: could not load network credentials: {e}")
        finally:
            self._net_loading_credentials = False

    def _net_save_credentials(self):
        if getattr(self, "_net_loading_credentials", False):
            return
        ssid = self.net_ssid_edit.text().strip()
        password = self.net_pass_edit.text()
        if not ssid and not password:
            return
        data = {
            "module": self.net_module_combo.currentText(),
            "ssid": ssid,
            "password": password,
        }
        path = self._net_credentials_path()
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:  # noqa: BLE001 - surface save problems without blocking entry
            self._net_log(f"WARNING: could not save network credentials: {e}")

    def _net_log(self, msg):
        self.net_log.append(f"{datetime.now():%H:%M:%S}  {msg}")
        self.net_log.moveCursor(QTextCursor.MoveOperation.End)
        # keep the UI responsive during the long RN131 sequence
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

    def _net_require_serial(self):
        if getattr(self, "connection_type_combo", None) and \
                self.connection_type_combo.currentText() != "Serial":
            self._net_log("ERROR: network config requires a SERIAL connection (not WiFi).")
            return False
        if not self.serial_port or not self.serial_port.is_open:
            self._net_log("ERROR: not connected. Connect to the PMC-Eight serial port on the "
                          "Configurator tab first.")
            return False
        return True

    def _net_write(self, data, settle=None):
        """Raw write — '@' is the passthrough AT terminator, already in `data`.

        After flushing, wait `settle` seconds so the module has time to start
        processing before we read its reply. This is what prevents the ESP-AT
        'busy p...' notice that appears when the next read/command arrives too
        soon. `settle` defaults to `self._net_settle` (set per module — the
        ESP32 is slower than the ESP8266, so it gets a longer delay).
        """
        self.serial_port.write(data.encode("ascii"))
        self.serial_port.flush()
        if settle is None:
            settle = getattr(self, "_net_settle", 0.15)
        if settle:
            time.sleep(settle)

    def _net_read(self, want=None, tries=10, per_read=0.3):
        """Read up to tries*per_read seconds; stop early once `want` is seen.

        The module often replies in bursts with gaps between them, and the
        ESP-AT firmware can interpose a 'busy p...' notice before the real
        result. So when we're waiting for a specific token we keep polling the
        full window across gaps instead of returning at the first pause — a gap
        is not the end of a slow reply. Only when no token is wanted do we stop
        at the first gap (read whatever came back).
        """
        acc = ""
        old = self.serial_port.timeout
        try:
            self.serial_port.timeout = per_read
            for _ in range(tries):
                chunk = self.serial_port.read(256)
                if chunk:
                    acc += chunk.decode("ascii", errors="replace")
                    if want and want in acc:
                        break
                elif acc and not want:
                    # Got data and weren't waiting for a specific token — done.
                    break
                # else: gap (or a 'busy' still in progress) while waiting for
                # `want` — keep polling the rest of the window.
        finally:
            self.serial_port.timeout = old
        return acc

    @staticmethod
    def _net_extract_ip(text):
        # Return the first *routable* address. A booted-but-unjoined module
        # reports 0.0.0.0 on interfaces that aren't up (e.g. the station
        # interface before it joins a home network); those are not real
        # addresses, so skip them and only fall back to 0.0.0.0 if nothing
        # else is present.
        ips = re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", text or "")
        for ip in ips:
            if ip != "0.0.0.0":
                return ip
        return ips[0] if ips else ""

    def _net_apply_known_ip(self, ip):
        """Remember the module's last-known IP and surface it in both places:
        the Network tab's read-only display, and the Configurator tab's WiFi IP
        field — so a later 'Connect via WiFi' is pre-filled with the address we
        just read or assigned. Called from every get/set path that yields a
        real address."""
        if not ip:
            return
        self._net_last_ip = ip
        self.net_ip_edit.setText(ip)
        field = getattr(self, "ip_edit", None)   # Configurator-tab WiFi field
        if field is not None:
            field.setText(ip)

    def _net_report_ip(self, module, resp):
        ip = self._net_extract_ip(resp)
        if ip:
            self._net_apply_known_ip(ip)
            self._net_log(f"Current {module} WiFi address: {ip}")
        else:
            raw = (resp or "").replace("\r", " ").replace("\n", " ").strip()
            self._net_log(f"Could not read {module} WiFi address. Raw: {raw}")

    def get_wifi_address(self):
        if not self._net_require_serial():
            return
        module = self.net_module_combo.currentText()
        try:
            self.serial_port.reset_input_buffer()
            if module in ("ESP32", "ESP8266"):
                self._net_read_esp_ip(module)
            else:
                self._net_read_rn131_ip()
        except Exception as e:  # noqa: BLE001 - surface any serial error to the log
            self._net_log(f"ERROR reading WiFi address: {e}")
        finally:
            try:
                self._net_write("###")
                self._net_log("Exited passthrough mode (###).")
            except Exception:  # noqa: BLE001
                pass

    def _net_read_esp_ip(self, module):
        self._net_settle = 0.6 if module == "ESP32" else 0.35
        self._net_log(f"Reading current {module} WiFi address...")
        self._net_write("ESPw42!")                      # enter AT passthrough
        time.sleep(0.2)
        self.serial_port.reset_input_buffer()

        found = False
        for _ in range(3):
            self._net_write("AT@")
            if "OK" in self._net_read(want="OK", tries=6):
                found = True
                break
        if not found:
            self._net_log("WARNING: no AT OK - check module selection / connection.")

        # Wait for the actual address line, not just the first burst: a slow
        # ESP32 may echo the command, pause, then send the reply. The markers
        # below are subnet-independent (unlike matching "192"); if one never
        # arrives, _net_read still polls the full window and the regex extracts
        # whatever address is present.
        if module == "ESP8266":
            # AT+CIFSR reports both the SoftAP IP (APIP) and the station IP
            # (STAIP) in one reply. On a freshly-booted PMC-Eight the module is
            # in AP mode at 192.168.47.1 and STAIP is 0.0.0.0; after joining a
            # home network STAIP holds the DHCP address. _net_extract_ip skips
            # 0.0.0.0, so the right one is reported in either state.
            self._net_write("AT+CIFSR@")
            resp = self._net_read(want="+CIFSR", tries=12, per_read=0.4)
        else:
            # ESP32: CIPSTA? is the *station* interface, which stays 0.0.0.0
            # until the module joins a home network — that is why "Get WiFi
            # Address" returned 0.0.0.0 on a fresh boot. The default 192.168.47.1
            # lives on the SoftAP interface (CIPAP?), so read both and let
            # _net_extract_ip pick the first routable address: the station IP if
            # joined, otherwise the AP IP.
            self._net_write("AT+CIPSTA?@")
            resp = self._net_read(want="+CIPSTA", tries=12, per_read=0.4)
            self._net_write("AT+CIPAP?@")
            resp += self._net_read(want="+CIPAP", tries=12, per_read=0.4)
        self._net_report_ip(module, resp)

    def _net_read_rn131_ip(self):
        self._net_settle = 0.3
        module = "RN131"
        self._net_log("Reading current RN131 WiFi address...")
        self._net_write("ESPw42")                       # RN131 enter (no '!')
        time.sleep(0.2)
        self.serial_port.reset_input_buffer()
        self._net_write("get ip a@")
        # Same idea: keep polling across gaps for the IP= line; falls through to
        # the full window if the marker never appears, then the regex extracts.
        resp = self._net_read(want="IP=", tries=12, per_read=0.4)
        self._net_report_ip(module, resp)

    # ── forward: configure for home network ──────────────────────────
    def configure_home_network(self):
        if not self._net_require_serial():
            return
        module = self.net_module_combo.currentText()
        ssid = self.net_ssid_edit.text().strip()
        pwd = self.net_pass_edit.text()
        if not ssid:
            self._net_log("ERROR: enter the home WiFi SSID.")
            return
        self._net_save_credentials()
        try:
            self.serial_port.reset_input_buffer()
            if module in ("ESP32", "ESP8266"):
                self._net_configure_esp(module, ssid, pwd)
            else:
                self._net_configure_rn131(ssid, pwd)
        except Exception as e:  # noqa: BLE001 - surface any serial error to the log
            self._net_log(f"ERROR during configure: {e}")
        finally:
            # ESPw42! put the PMC-Eight in passthrough; '###' (bare, no '@') tells
            # the Propeller to exit it. MUST run on success AND error, or the mount
            # is left stuck in passthrough. (Matches the VB tool's Write("###").)
            try:
                self._net_write("###")
                self._net_log("Exited passthrough mode (###).")
            except Exception:  # noqa: BLE001
                pass

    def _net_configure_esp(self, module, ssid, pwd):
        # Settle delay after each command before reading the reply. The ESP32 is
        # slower to turn a command around than the ESP8266, so give it more time;
        # both have headroom to go slower, which avoids the 'busy p...' notice.
        self._net_settle = 0.6 if module == "ESP32" else 0.35
        self._net_log(f"Configuring {module} for home network '{ssid}'...")
        self._net_write("ESPw42!")                      # enter AT passthrough
        time.sleep(0.2)
        self.serial_port.reset_input_buffer()

        found = False
        for _ in range(3):                              # probe (clears echo, finds OK)
            self._net_write("AT@")
            if "OK" in self._net_read(want="OK", tries=6):
                found = True
                break
        self._net_log("Found module (AT OK)." if found
                      else "WARNING: no AT OK — check module selection / connection.")

        self._net_write("AT+CWMODE=1@")                 # station mode
        self._net_log("Set station mode: " + ("OK" if "OK" in self._net_read(want="OK") else "?"))

        self._net_write(f'AT+CWJAP="{ssid}","{pwd}"@')  # join
        self._net_log("Joining home network (can take several seconds)...")
        joined = "GOT" in self._net_read(want="GOT", tries=30, per_read=0.5)
        self._net_read(want="OK", tries=10)
        self._net_log("Joined home network." if joined
                      else "WARNING: did not see 'WIFI GOT IP'.")

        ip_cmd = "AT+CIFSR@" if module == "ESP8266" else "AT+CIPSTA?@"
        self._net_write(ip_cmd)
        resp = self._net_read(want="192", tries=12, per_read=0.4)
        ip = self._net_extract_ip(resp)
        if ip:
            self._net_apply_known_ip(ip)
            self._net_log(f"Assigned IP: {ip}")
        else:
            self._net_log("Could not read assigned IP. Raw: "
                          + resp.replace("\r", " ").replace("\n", " ").strip())

    def _net_configure_rn131(self, ssid, pwd):
        self._net_settle = 0.3                          # RN131 settle per command
        self._net_log(f"Configuring RN131 for home network '{ssid}'...")
        self._net_write("ESPw42")                       # RN131 enter (no '!')
        time.sleep(0.2)
        self.serial_port.reset_input_buffer()
        for cmd in (
            f"set wlan ssid {ssid}@",
            f"set wlan pass {pwd}@",
            "set wlan join 1@",
            "set wlan chan 0@",
            "set ip dhcp 1@",
            "set ip host 0.0.0.0@",
            "set comm remote 1@",
            "set ip remote 0@",
            "save@",
        ):
            self._net_write(cmd)
            self._net_read(tries=4)
            self._net_log(cmd)
            time.sleep(0.1)
        self._net_write("reboot@")
        self._net_log("reboot — RN131 joining home network (waiting ~8 s)...")
        time.sleep(8)

        self._net_write("ESPw42")                       # re-enter to read IP
        time.sleep(0.2)
        self.serial_port.reset_input_buffer()
        self._net_write("get ip a@")
        resp = self._net_read(want="192", tries=12, per_read=0.4)
        ip = self._net_extract_ip(resp)
        if ip:
            self._net_apply_known_ip(ip)
            self._net_log(f"Assigned IP: {ip}")
        else:
            self._net_log("Could not read RN131 IP. Raw: " + resp.strip())

    # ── reverse: restore to default ──────────────────────────────────
    def restore_network_default(self):
        if not self._net_require_serial():
            return
        if self.net_module_combo.currentText() != "RN131":
            self._net_log("ESP modules restore on the next PMC-Eight reboot — use BOOT PMC8.")
            return
        try:
            self._net_settle = 0.3                       # RN131 settle per command
            self.serial_port.reset_input_buffer()
            self._net_log("Restoring RN131 to PMC-Eight factory default (AP mode)...")
            self._net_write("ESPw42!$$$")               # enter RN131 command mode
            time.sleep(0.2)
            self.serial_port.reset_input_buffer()
            # Ported verbatim from UFCT btnRestoreRn131_Click (interleaved saves).
            for cmd in (
                "set comm size 64@", "set dns addr 0.0.0.0@", "set dns backup 0.0.0.0@",
                "set dns name dns1@", "save@",
                "set ftp addr 0.0.0.0@", "set ftp time 200@", "set ip dhcp 4@",
                "set ip flag 0x47@", "save@",
                "set ip gate 192.168.47.1@", "set ip addr 192.168.47.1@",
                "set ip net 255.255.0.0@", "save@",
                "set ip host 0.0.0.0@", "set ip protocol 0x03@",
                "set ip remote 54372@", "set ip local 54372@", "save@",
                "set sys autosleep 0@", "set sys sleep 0@", "set sys wake 5@",
                "set sys trigger 0x01@", "save@",
                "set wlan auth 4@", "set wlan hide 1@", "set wlan join 7@",
                "set wlan chan 11@", "save@",
                "set opt deviceid PMC-Eight@", "set wlan passphrase PMC-Eight@",
                "set apmode passphrase PMC-Eight@", "set wlan ext_antenna 1@",
            ):
                self._net_write(cmd)
                self._net_read(tries=3)
                self._net_log(cmd)
                time.sleep(0.1)
            self._net_log("Saving final configuration (wait ~10 s)...")
            self._net_write("save@")
            time.sleep(10)
            self._net_write("reboot@")
            self._net_read(tries=3)
            self._net_write("###@")                     # exit passthrough mode
            self._net_log("RN131 restore to PMC-Eight default complete.")
        except Exception as e:  # noqa: BLE001
            self._net_log(f"ERROR during restore: {e}")
