"""
Network Management — multiplatform PMC-Eight WiFi configuration.

Mixin for PMC8Configurator (PMC8_Dashboard.py). Adds a "Network" tab that
configures the PMC-Eight WiFi module to join a home network, or restores it to
factory default — for all three module types, over the existing serial link:

  * ESP32   : ESPw42!  + AT+CWMODE=1 / AT+CWJAP / AT+CIPSTA?  (IP via CIPSTA?)
  * ESP8266 : ESPw42!  + AT+CWMODE=1 / AT+CWJAP / AT+CIFSR    (IP via CIFSR)
  * RN131   : ESPw42 then '$$$' + set wlan ... / save / reboot (IP via get ip a)

Restore-to-default:
  * ESP32 / ESP8266 : nothing to do — the module reverts on the next PMC-Eight
    reboot (use BOOT PMC8 on the Configurator tab).
  * RN131 : full factory-default AP restore (192.168.47.1, SSID/passphrase
    "PMC-Eight", TCP+UDP 54372) — ported from the UFCT "Restore RN131" routine.

Framing: the PMC-Eight serial passthrough uses '@' as the AT line terminator, so
commands carry their own '@'. The mode-enter tokens (ESPw42! for the ESP modules,
ESPw42 for the RN131) and the passthrough-exit (###) are sent verbatim.

The RN131 needs a SECOND step the ESP modules don't. ESPw42 only opens the
PMC-Eight passthrough; the module itself is still in *data* mode, where it
forwards received bytes to the TCP link instead of parsing them as commands. A
bare '$$$' (no '@' terminator, no '!') is the WiFly escape into command mode, and
the module answers 'CMD'. Leave command mode with 'exit@' when done — '###' only
closes the PMC-Eight passthrough, and a module left in command mode has no data
link until it reboots.

The RN131 flows mirror the "Configure PMC8 for Home Network Connection" VB tool;
the restore mirrors the UFCT "Restore RN131" routine. Only the WinForms shell is
replaced by Qt, so this runs unchanged on Windows / macOS / Linux.

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

    def _net_read(self, want=None, tries=10, per_read=0.3, stop=None):
        """Read up to tries*per_read seconds; stop early once `want` is seen (or
        the optional `stop(acc)` predicate returns True).

        The module often replies in bursts with gaps between them, and the
        ESP-AT firmware can interpose a 'busy p...' notice before the real
        result. So when we're waiting for a specific token we keep polling the
        full window across gaps instead of returning at the first pause — a gap
        is not the end of a slow reply. Only when neither `want` nor `stop` is
        given do we stop at the first gap (read whatever came back).
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
                    if stop and stop(acc):
                        break
                elif acc and not want and not stop:
                    # Got data and weren't waiting for anything specific — done.
                    break
                # else: gap (or a 'busy' still in progress) while waiting for
                # `want`/`stop` — keep polling the rest of the window.
        finally:
            self.serial_port.timeout = old
        return acc

    # A complete, delimited dotted quad. The lookbehind/lookahead require a
    # non-digit boundary on both sides so a mid-arrival fragment (e.g. the
    # '192.168.0.4' of an incoming '192.168.0.40') can't be mistaken for a whole
    # address — we wait for the trailing delimiter before accepting it.
    _IP_STOP_RE = re.compile(r"(?<![\d.])\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?=[\s:,])")

    def _net_reply_has_ip(self, text):
        """Stop condition for a 'get ip a' read: True once the reply carries the
        address. Accepts an 'IP=' marker (firmware that prefixes it) OR a bare,
        complete, routable dotted quad — WiFly 4.75 answers with just
        '192.168.0.40', no 'IP='. Without this the read waits out the whole
        window for an 'IP=' token that never comes."""
        if "IP=" in text:
            return True
        return any(ip != "0.0.0.0" for ip in self._IP_STOP_RE.findall(text or ""))

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

    def _net_wait(self, seconds, label):
        """Responsive wait (keeps the GUI alive) with start/done log notes."""
        from PyQt6.QtWidgets import QApplication
        self._net_log(f"{label} — waiting {seconds}s...")
        end = time.time() + seconds
        while time.time() < end:
            QApplication.processEvents()
            time.sleep(0.05)
        self._net_log(f"{label} — done.")

    def _module_is_rn131(self):
        """True when the WiFi module is (or is selected as) an RN131. Fast
        Server / Envision does not exist on RN131, so every ESGe!/ESSe* probe
        must be skipped for it — on an RN131 those commands just time out with
        no reply and waste seconds. Either the Network-tab selection or a module
        type detected by Get Configuration being RN131 is enough."""
        combo = getattr(self, "net_module_combo", None)
        if combo is not None and combo.currentText() == "RN131":
            return True
        return getattr(self, "_wifi_type", None) == "RN131"

    def _rn131_wlan_value(self, value):
        """Encode an SSID or passphrase for a WiFly 'set wlan ...' command.

        WiFly tokenises the command line on spaces, so 'set wlan pass a b c'
        stores only 'a' — the module then fails authentication (AUTH-ERR) and
        loops trying to join. WiFly's convention is to send each space as '$',
        which it converts back to a real space when it stores the value. The
        saved credential keeps the real spaces; only the on-wire value is
        encoded. A literal '$' can't be represented (WiFly would read it as a
        space), so the caller warns about that separately."""
        return value.replace(" ", "$")

    def _envision_suspend_for_at(self, wait_s=5):
        """Envision (Fast Server) mode takes over the AT command processor, so
        WiFi-address / home-network operations fail while it is running. Query
        ESGe!; if the 'currently on' bit is set (value >= 4), send ESSe0! to
        stop it and wait `wait_s` for the module. Returns True if Envision was
        active (caller MUST restore with _envision_restore_after_at)."""
        if self._module_is_rn131():
            return False  # RN131 has no Fast Server/Envision — never probe ESGe!
        if not self.serial_port or not self.serial_port.is_open:
            return False
        try:
            reply = self._raw_serial_query(self.serial_port, "ESGe!", timeout=3.0)
        except Exception as e:  # noqa: BLE001
            self._net_log(f"Envision pre-check skipped: {e}")
            return False
        self._net_log(f"Envision check — ESGe! -> {reply or '(no reply)'}")
        state = self._parse_esge(reply)
        if state is None or state < 4:
            return False
        self._net_log("Envision (Fast Server) is ACTIVE — stopping it (ESSe0!) so the "
                      "AT command processor is free.")
        try:
            self._raw_serial_command(self.serial_port, "ESSe0!")
        except Exception as e:  # noqa: BLE001
            self._net_log(f"Could not send ESSe0!: {e}")
            return False
        self._net_wait(wait_s, "WiFi module rebooting")
        try:
            self.serial_port.reset_input_buffer()
        except Exception:  # noqa: BLE001
            pass
        return True

    def _envision_restore_after_at(self, was_active):
        """Re-enable Envision (Fast Server) with ESSe1! if it was active before
        we suspended it for the AT operation."""
        if not was_active:
            return
        if not self.serial_port or not self.serial_port.is_open:
            self._net_log("NOTE: Envision not restored (serial not open); it returns "
                          "on the next PMC-Eight reboot.")
            return
        try:
            self._raw_serial_command(self.serial_port, "ESSe1!")
            self._net_log("Restored Envision (Fast Server) to active (ESSe1!).")
        except Exception as e:  # noqa: BLE001
            self._net_log(f"Could not restore Envision (ESSe1!): {e}")

    def get_wifi_address(self):
        if not self._net_require_serial():
            return
        was_active = self._envision_suspend_for_at(5)
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
            self._envision_restore_after_at(was_active)

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

    def _net_discard_buffers(self):
        """Drop anything queued in both directions (the VB tool's DiscardIn/Out
        before each RN131 step) so a reply can't be read as the previous one."""
        for reset in (self.serial_port.reset_output_buffer,
                      self.serial_port.reset_input_buffer):
            try:
                reset()
            except Exception:  # noqa: BLE001 - buffer resets are best-effort
                pass

    def _net_rn131_escape(self, wait_s):
        """Send the bare '$$$' WiFly escape and return the reply.

        '$$$' takes NO '@' terminator — it is not a passthrough AT line, it is
        the module's own escape sequence — and WiFly wants a quiet guard time
        either side of it, so nothing is appended and nothing follows until the
        wait elapses."""
        self._net_write("$$$", settle=0)
        time.sleep(wait_s)
        return self._net_read(want="CMD", tries=4, per_read=0.3)

    def _net_rn131_command_mode(self, passthrough=True, wait_s=2.0):
        """Put the RN131 into command mode; return True once it answers 'CMD'.

        Two steps, and the second is the one that was missing: ESPw42 opens the
        PMC-Eight passthrough (no '!' — unlike the ESP modules), then a separate
        bare '$$$' escapes the module itself into command mode. Without the
        '$$$' the module stays in data mode and silently forwards 'get ip a@' to
        the TCP link instead of answering it.

        `wait_s` mirrors the VB GET IP routine's 2 s pause after '$$$' (its v1.1
        notes tie the GET IP fix to this step); the config routine used 300 ms.
        A longer guard time is never harmful, only slower.

        Pass passthrough=False after a module reboot: the reboot drops the
        module's command mode but NOT the PMC-Eight passthrough, which is a
        Propeller state — so only the '$$$' needs re-sending."""
        if passthrough:
            self._net_write("ESPw42")                   # RN131 enter (no '!')
            time.sleep(0.2)
            self._net_read(tries=2)                     # drain the banner
        self._net_discard_buffers()
        reply = self._net_rn131_escape(wait_s)
        if "Auto-" in reply:
            # Module was mid-association and answered with its Auto-Assoc notice
            # instead of taking the escape. The VB tool re-sends once here.
            self._net_log("RN131 is still associating — re-sending $$$...")
            reply = self._net_rn131_escape(wait_s)
        if "CMD" in reply:
            self._net_log("RN131 in command mode (CMD).")
            return True
        if "AUTH-ERR" in reply or "Disconn" in reply:
            # The module is looping on a failed join (usually a wrong/truncated
            # passphrase saved earlier). The constant status spam violates the
            # quiet guard time the '$$$' escape needs, so command mode can't be
            # entered until the join storm stops.
            self._net_log("RN131 is failing to authenticate to the saved network "
                          "(AUTH-ERR) and is stuck retrying, which blocks command "
                          "mode. Click 'Restore to Default' first, then 'Configure "
                          "for Home Network' again with the correct password. If it "
                          "still fails with the right password, note the RN131 is "
                          "2.4GHz WPA/WPA2 only — it cannot join a WPA3-only network "
                          "or one that requires protected management frames (PMF). "
                          "A 2.4GHz WPA2 SSID (like a guest/IoT network) is safest.")
            return False
        self._net_log("Failed to enter RN131 command mode — check the module type. "
                      f"Reply: {reply.strip() or '(no reply)'}")
        return False

    def _net_rn131_exit_command_mode(self):
        """Return the RN131 to data mode. MUST run once command mode is entered:
        '###' only closes the PMC-Eight passthrough, so a module left in command
        mode keeps its data link dead until it reboots."""
        try:
            self._net_write("exit@")
            time.sleep(0.1)
            self._net_log("Left RN131 command mode (exit).")
        except Exception as e:  # noqa: BLE001 - never mask the original error
            self._net_log(f"WARNING: could not leave RN131 command mode: {e}")

    def _net_rn131_get_ip(self):
        """Query the module's address (requires command mode). The RN131 echoes
        the command before answering; _net_read accumulates the whole window and
        _net_extract_ip picks the address out, so the echo is harmless — it
        carries no digits.

        The read stops as soon as the address is in hand (via _net_reply_has_ip),
        whether the firmware prefixes it with 'IP=' or returns the bare address
        as WiFly 4.75 does — so a bare-address reply no longer waits out the full
        window for an 'IP=' that never arrives.

        A '?-' reply means the module lost the command's first character. The VB
        tool retries by re-sending it split after the 'g', which is mirrored
        here rather than tidied away — it reads like a real field workaround."""
        self._net_discard_buffers()
        self._net_write("get ip a@")
        resp = self._net_read(stop=self._net_reply_has_ip, tries=12, per_read=0.4)
        if "?-" in resp:
            self._net_log("RN131 garbled the command (?-) — retrying...")
            self._net_write("g")
            self._net_discard_buffers()
            self._net_write("et ip a@")
            resp = self._net_read(stop=self._net_reply_has_ip, tries=12, per_read=0.4)
        return resp

    def _net_read_rn131_ip(self):
        self._net_settle = 0.3
        module = "RN131"
        self._net_log("Reading current RN131 WiFi address...")
        if not self._net_rn131_command_mode():
            return
        try:
            self._net_report_ip(module, self._net_rn131_get_ip())
        finally:
            self._net_rn131_exit_command_mode()

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
        was_active = self._envision_suspend_for_at(5)
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
            self._envision_restore_after_at(was_active)

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

        # WiFly splits 'set wlan ...' on spaces, so encode spaces as '$'. Without
        # this a space in the SSID or password is truncated at the first space
        # and the module fails to authenticate (AUTH-ERR).
        if " " in ssid or " " in pwd:
            self._net_log("Note: encoding space(s) in the SSID/password as '$' "
                          "for the RN131 (WiFly space convention).")
        if "$" in ssid or "$" in pwd:
            self._net_log("WARNING: a literal '$' in the SSID or password can't be "
                          "sent to an RN131 (WiFly reads '$' as a space). If the "
                          "join fails, the RN131 can't use this password.")
        ssid_enc = self._rn131_wlan_value(ssid)
        pwd_enc = self._rn131_wlan_value(pwd)

        if not self._net_rn131_command_mode():
            return
        in_command_mode = True
        try:
            for cmd in (
                f"set wlan ssid {ssid_enc}@",
                f"set wlan pass {pwd_enc}@",
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

            # The reboot drops command mode (and the module comes back in data
            # mode), so there is nothing to exit until we re-enter below.
            self._net_write("reboot@")
            in_command_mode = False
            self._net_wait(8, "RN131 rebooting and joining home network")

            # Re-enter command mode to read the assigned address. The passthrough
            # survives the module reboot, so only the '$$$' is re-sent — and the
            # module may still be associating, which _net_rn131_command_mode
            # retries past.
            if not self._net_rn131_command_mode(passthrough=False):
                self._net_log("Could not re-enter command mode to read the IP — "
                              "the module may still be joining. Use Get WiFi "
                              "Address in a moment to read it.")
                return
            in_command_mode = True
            resp = self._net_rn131_get_ip()
            ip = self._net_extract_ip(resp)
            if ip:
                self._net_apply_known_ip(ip)
                self._net_log(f"Assigned IP: {ip}")
            else:
                self._net_log("Could not read RN131 IP. Raw: " + resp.strip())
        finally:
            if in_command_mode:
                self._net_rn131_exit_command_mode()

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
