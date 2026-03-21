#!/usr/bin/env python3
"""
PMC8 ESP32 OTA Firmware Update Script

Performs over-the-air firmware updates on the ESP32 module inside a PMC8
telescope mount controller. See OTAScriptDescription.txt for full details.

Requirements:
    pip install pyserial
"""

import sys
import os
import time
from datetime import datetime
import socket
import subprocess
import threading
import http.server
import functools
import re
import argparse

try:
    import serial
except ImportError:
    print("pyserial is required but not installed.")
    answer = input("Install it now? (y/n): ").strip().lower()
    if answer == "y":
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyserial"])
        except Exception as e:
            print(f"ERROR: pip install failed: {e}")
            print("Try running manually:  pip install pyserial")
            sys.exit(1)
        # Verify it installed successfully
        try:
            import serial
            print(f"pyserial {serial.VERSION} installed successfully.")
        except ImportError:
            print("ERROR: pyserial installation failed.")
            sys.exit(1)
    else:
        print("Cannot continue without pyserial.")
        sys.exit(1)


# ── Constants ────────────────────────────────────────────────────────────────

BAUD_RATE = 115200
HTTP_PORT = 8000
DEFAULT_FIRMWARE_FILE = "esp-at.bin"
FIREWALL_RULE_NAME = "PMC8 OTA"

# PMC8 AP mode network
PMC8_AP_SUBNET = "192.168.47."
PMC8_AP_IP = "192.168.47.1"
PMC8_AP_EXPECTED_PC_IP = "192.168.47.11"

# Timeouts (seconds)
AT_TIMEOUT = 5
WIFI_JOIN_TIMEOUT = 45
OTA_TIMEOUT = 180
REBOOT_WAIT = 20


# ── Helpers ──────────────────────────────────────────────────────────────────

def log(phase, msg):
    print(f"[{phase}] {msg}")


def scan_firmware_version(fw_path):
    """Scan a firmware binary for the embedded version string.

    Looks for the version pattern (e.g., "ES4.2.0" or "4.2.0") and module name
    (e.g., "WROOM-32") that AT+GMR reports as "Bin version:ES4.2.0(WROOM-32)".

    Returns (version, module) tuple, or (None, None) if not found.
    """
    with open(fw_path, "rb") as f:
        data = f.read(0x5000)  # version info is near the start
    # Match version with optional prefix (e.g., "ES4.2.0", "4.2.0", "v2.0.0")
    ver_match = re.search(rb'(\w*\d+\.\d+\.\d+)', data)
    mod_match = re.search(rb'(WROOM-\d+|WROVER-\d+|MINI-\d+|PICO-\w+)', data)
    version = ver_match.group(1).decode("ascii") if ver_match else None
    module = mod_match.group(1).decode("ascii") if mod_match else None
    return (version, module)


def read_response(ser, timeout=AT_TIMEOUT, expect=None):
    """Read serial data until timeout or until `expect` string is found."""
    ser.timeout = timeout
    buf = b""
    deadline = time.time() + timeout
    while time.time() < deadline:
        chunk = ser.read(ser.in_waiting or 1)
        if chunk:
            buf += chunk
            text = buf.decode("ascii", errors="replace")
            if expect and expect in text:
                return text
        else:
            time.sleep(0.05)
    return buf.decode("ascii", errors="replace")


def send_at(ser, cmd, timeout=AT_TIMEOUT, expect="OK"):
    """Send an AT command (with @ terminator) and wait for expected response."""
    full = cmd + "@"
    for ch in full:
        ser.write(ch.encode("ascii"))
        time.sleep(0.005)
    resp = read_response(ser, timeout=timeout, expect=expect)
    return resp


def send_es(ser, cmd, timeout=AT_TIMEOUT):
    """Send an ES command (no special terminator) and read response."""
    for ch in cmd:
        ser.write(ch.encode("ascii"))
        time.sleep(0.005)
    return read_response(ser, timeout=timeout, expect="!")


def get_local_ip():
    """Get the host PC's local IP address (the one on the LAN, not 127.0.0.1)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def detect_ap_mode():
    """Check if the PC is connected directly to the PMC8's WiFi AP.

    Returns the PC's IP on the AP network if detected, or None.
    The PMC8 AP assigns 192.168.47.11 to the first client.
    """
    try:
        # Try to reach the PMC8 AP gateway to discover our IP on that subnet
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect((PMC8_AP_IP, 80))
            local_ip = s.getsockname()[0]
        finally:
            s.close()
        if local_ip.startswith(PMC8_AP_SUBNET):
            return local_ip
    except OSError:
        pass
    return None


def add_firewall_rule():
    """Add a temporary Windows Firewall rule for the OTA HTTP server."""
    try:
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "add", "rule",
             "name=" + FIREWALL_RULE_NAME, "dir=in", "action=allow",
             "protocol=TCP", "localport=" + str(HTTP_PORT)],
            capture_output=True, check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def remove_firewall_rule():
    """Remove the temporary Windows Firewall rule."""
    try:
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "delete", "rule",
             "name=" + FIREWALL_RULE_NAME],
            capture_output=True, check=False
        )
    except FileNotFoundError:
        pass


def start_http_server(bind_ip, directory):
    """Start an HTTP server in a background thread. Returns the thread."""
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=directory
    )
    httpd = http.server.HTTPServer((bind_ip, HTTP_PORT), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def check_pmc8_version(version_resp):
    """Check if the PMC8 Propeller firmware version supports ExplorestarsLite.

    Parses the ESGv! response (e.g., "ESGvES20A02.1.8.2.bt Release ...!")
    and checks if the version is >= 1.8.2 (the minimum for HTTP bridge support).

    Returns (version_string, is_compatible) tuple.
    """
    # Extract version like "20A02.1.8.2" from the response
    match = re.search(r'20A0(\d+)\.(\d+)\.(\d+)\.(\d+)', version_resp)
    if not match:
        return (None, False)
    series = int(match.group(1))
    major = int(match.group(2))
    minor = int(match.group(3))
    patch = int(match.group(4))
    version_str = f"20A0{series}.{major}.{minor}.{patch}"
    # Compatible if series > 2, or series == 2 and version >= 1.8.2
    if series > 2:
        return (version_str, True)
    if series == 2:
        if (major, minor, patch) >= (1, 8, 2):
            return (version_str, True)
    return (version_str, False)


def verify_http_bridge(esp_ip):
    """Send a request to the HTTP bridge to verify it works."""
    import urllib.request
    url = f"http://{esp_ip}/cmd?q=ESGv!"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.read().decode("ascii", errors="replace")
    except Exception as e:
        return f"ERROR: {e}"


# ── Main Script ──────────────────────────────────────────────────────────────

def main():
    print()
    print("=" * 60)
    print("  PMC8 ESP32 OTA Firmware Update")
    print("=" * 60)
    print()
    print("  This script supports two connection modes:")
    print()
    print("  DIRECT (AP mode):")
    print("    PC is connected to the PMC8's WiFi network (192.168.47.x).")
    print("    No home WiFi needed. The script auto-detects this mode")
    print(f"    when your PC's IP is {PMC8_AP_EXPECTED_PC_IP}.")
    print("    To ensure this, disconnect other clients from the PMC8")
    print("    and reconnect your PC so it gets the first IP.")
    print()
    print("  LAN mode:")
    print("    PC is on a home WiFi network. The script will connect")
    print("    the ESP32 to your home WiFi for the update, then it")
    print("    returns to AP mode on next power cycle.")
    print()
    print("-" * 60)

    parser = argparse.ArgumentParser(description="PMC8 ESP32 OTA Firmware Update")
    parser.add_argument("--port", help="COM port (e.g., COM3)")
    parser.add_argument("--ssid", help="WiFi SSID (LAN mode only)")
    parser.add_argument("--password", help="WiFi password (LAN mode only)")
    parser.add_argument("--firmware", help="Firmware binary filename (default: esp-at.bin)")
    args = parser.parse_args()

    in_passthrough = False
    httpd = None
    firewall_added = False
    ser = None

    try:
        # ── Phase 1: Validate Environment ────────────────────────────────
        log("Phase 1", "Validating environment")

        # Detect AP mode: is the PC on the PMC8's WiFi network?
        ap_ip = detect_ap_mode()
        ap_mode = False
        if ap_ip:
            if ap_ip == PMC8_AP_EXPECTED_PC_IP:
                ap_mode = True
                log("Phase 1", f"DIRECT mode detected — PC is at {ap_ip} on PMC8 AP network")
                log("Phase 1", f"ESP32 is at {PMC8_AP_IP}, no WiFi join needed")
            else:
                log("Phase 1", f"PC is on PMC8 subnet ({ap_ip}) but not at expected {PMC8_AP_EXPECTED_PC_IP}")
                log("Phase 1", "For safety, disconnect other clients from the PMC8 WiFi,")
                log("Phase 1", "then disconnect and reconnect your PC to get 192.168.47.11.")
                log("Phase 1", "This ensures no other client interferes during the OTA update.")
                raise SystemExit(1)
        else:
            log("Phase 1", "LAN mode — will connect ESP32 to home WiFi for update")

        com_port = args.port or input("Enter COM port (e.g., COM3): ").strip()

        if not ap_mode:
            ssid = args.ssid or input("Enter WiFi SSID: ").strip()
            password = args.password or input("Enter WiFi password: ").strip()
        else:
            ssid = None
            password = None

        script_dir = os.path.dirname(os.path.abspath(__file__))
        fw_name = args.firmware
        if not fw_name:
            fw_name = input(f"Firmware filename [{DEFAULT_FIRMWARE_FILE}]: ").strip()
            if not fw_name:
                fw_name = DEFAULT_FIRMWARE_FILE
        fw_path = os.path.join(script_dir, fw_name)
        if not os.path.isfile(fw_path):
            log("Phase 1", f"ERROR: {fw_name} not found in {script_dir}")
            sys.exit(1)
        fw_size = os.path.getsize(fw_path)
        log("Phase 1", f"Firmware: {fw_name} ({fw_size:,} bytes)")

        if fw_size > 2 * 1024 * 1024:
            log("Phase 1", f"ERROR: {fw_name} is {fw_size:,} bytes — too large for OTA.")
            log("Phase 1", "This looks like a full 4MB factory image (factory_WROOM-32.bin).")
            log("Phase 1", "OTA requires the app-only binary (esp-at.bin), which is under 2MB.")
            log("Phase 1", "To flash the full image, use the serial method — see FLASH_QUICK_START.txt.")
            sys.exit(1)

        # Scan the binary for the embedded version string
        fw_version, fw_module = scan_firmware_version(fw_path)
        if fw_version:
            fw_label = f"{fw_version}({fw_module})" if fw_module else fw_version
            log("Phase 1", f"Firmware binary version: {fw_label}")
        else:
            log("Phase 1", "WARNING: Could not detect version from firmware binary.")
            fw_label = None

        input("Confirm PMC8 is powered on and running, then press Enter...")

        log("Phase 1", f"Opening {com_port} at {BAUD_RATE} baud")
        ser = serial.Serial()
        ser.port = com_port
        ser.baudrate = BAUD_RATE
        ser.timeout = AT_TIMEOUT
        ser.dtr = False
        ser.rts = False
        try:
            ser.open()
        except serial.SerialException as e:
            log("Phase 1", f"ERROR: Could not open {com_port}: {e}")
            log("Phase 1", "Check that the COM port is correct and not in use by another program")
            log("Phase 1", "(ExploreStars, SkySafari, terminal programs, etc.).")
            raise SystemExit(1)
        ser.reset_input_buffer()

        log("Phase 1", "COM port opened (DTR/RTS held low to avoid PMC8 reboot).")
        log("Phase 1", "Waiting 5 seconds for port to settle...")
        for i in range(5, 0, -1):
            print(f"\r  Settling: {i}s remaining ", end="", flush=True)
            time.sleep(1)
        print()
        ser.reset_input_buffer()

        # ── Phase 2: Enter Pass-Through Mode ─────────────────────────────
        log("Phase 2", "Entering ESP32 pass-through mode")
        log("Phase 2", "Sending ESPw42!...")
        resp = send_es(ser, "ESPw42!")
        log("Phase 2", f"ESPw42! response: [{resp.strip()}]")
        time.sleep(2)
        in_passthrough = True

        # Flush any boot or transition noise
        ser.reset_input_buffer()

        ok_received = False
        for attempt in range(5):
            resp = send_at(ser, "AT")
            log("Phase 2", f"AT attempt {attempt + 1} response: [{resp.strip()}]")
            if "OK" in resp:
                ok_received = True
                break
            time.sleep(1)

        if not ok_received:
            log("Phase 2", "ERROR: ESP32 not responding to AT commands")
            raise SystemExit(1)
        log("Phase 2", "ESP32 responding OK")

        # Get current firmware version before update
        log("Phase 2", "Sending ATE0 (disable echo)...")
        send_at(ser, "ATE0")
        time.sleep(0.3)

        log("Phase 2", "Querying current firmware version (AT+GMR)...")
        resp = send_at(ser, "AT+GMR", timeout=AT_TIMEOUT, expect="OK")
        old_bin_match = re.search(r'Bin version[:\s]*(.*)', resp)
        old_version = old_bin_match.group(1).strip() if old_bin_match else "unknown"
        log("Phase 2", f"Current ESP32 firmware: {old_version}")

        print()
        print(f"  Installed:  {old_version}")
        if fw_label:
            print(f"  Update to:  {fw_label}")
        else:
            print(f"  Update to:  {fw_name} (version unknown)")
        print()
        proceed = input("Do you want to update the firmware? (y/n): ").strip().lower()
        if proceed != "y":
            log("Phase 2", "Update cancelled by user.")
            raise SystemExit(0)
        print()

        # ── Phase 3: Connect ESP32 to Home WiFi (LAN mode only) ──────────
        if ap_mode:
            log("Phase 3", "DIRECT mode — skipping WiFi join (ESP32 is already the AP)")
            esp_ip = PMC8_AP_IP
            local_ip = ap_ip
        else:
            log("Phase 3", "Connecting ESP32 to home WiFi")

            log("Phase 3", "Sending AT+CWMODE=1 (station mode)...")
            resp = send_at(ser, "AT+CWMODE=1")
            log("Phase 3", f"Response: {resp.strip()}")
            time.sleep(0.5)

            wifi_joined = False
            for wifi_attempt in range(3):
                log("Phase 3", f'Sending AT+CWJAP="{ssid}","****" (attempt {wifi_attempt + 1})...')
                resp = send_at(ser, f'AT+CWJAP="{ssid}","{password}"',
                                timeout=WIFI_JOIN_TIMEOUT, expect="GOT IP")
                log("Phase 3", f"Response: {resp.strip()}")
                if "GOT IP" in resp:
                    wifi_joined = True
                    break
                log("Phase 3", "WiFi join failed, retrying...")
                time.sleep(2)
                ser.reset_input_buffer()

            if not wifi_joined:
                log("Phase 3", "ERROR: Failed to join WiFi after 3 attempts")
                raise SystemExit(1)
            log("Phase 3", "WiFi connected, got IP")

            # Flush any trailing log messages from the WiFi join
            time.sleep(3)
            ser.reset_input_buffer()

            log("Phase 3", "Sending AT+CIPSTA? (query IP address)...")
            resp = send_at(ser, "AT+CIPSTA?", expect="OK")
            log("Phase 3", f"Response: {resp.strip()}")
            ip_match = re.search(r'ip:"([^"]+)"', resp)
            if not ip_match:
                # Fallback: try AT+CIFSR
                log("Phase 3", "CIPSTA failed, trying AT+CIFSR...")
                time.sleep(1)
                ser.reset_input_buffer()
                resp = send_at(ser, "AT+CIFSR", expect="OK")
                log("Phase 3", f"CIFSR response: {resp.strip()}")
                # CIFSR format: +CIFSR:STAIP,"192.168.x.y"
                ip_match = re.search(r'STAIP,"([^"]+)"', resp)
            if not ip_match:
                log("Phase 3", "ERROR: Could not determine ESP32 IP address")
                raise SystemExit(1)
            esp_ip = ip_match.group(1)
            if esp_ip == "0.0.0.0":
                log("Phase 3", "ERROR: ESP32 got 0.0.0.0 — no real IP assigned")
                raise SystemExit(1)
            log("Phase 3", f"ESP32 IP: {esp_ip}")

            try:
                local_ip = get_local_ip()
            except OSError:
                log("Phase 3", "ERROR: Could not determine this PC's IP address.")
                log("Phase 3", "Ensure the PC is connected to the same network the ESP32 joined.")
                raise SystemExit(1)

        # ── Phase 4: Prepare HTTP Server ─────────────────────────────────
        log("Phase 4", "Preparing HTTP server")
        log("Phase 4", f"Host PC IP: {local_ip}")

        log("Phase 4", "Adding firewall rule")
        firewall_added = add_firewall_rule()
        if not firewall_added:
            log("Phase 4", "WARNING: Could not add firewall rule (may need admin).")
            log("Phase 4", "Ensure port 8000 is open manually if OTA fails.")

        log("Phase 4", f"Starting HTTP server on 0.0.0.0:{HTTP_PORT} (all interfaces)")
        try:
            httpd = start_http_server("0.0.0.0", script_dir)
        except OSError as e:
            log("Phase 4", f"ERROR: Could not start HTTP server on port {HTTP_PORT}: {e}")
            log("Phase 4", "Another program may be using this port. Close it and try again.")
            raise SystemExit(1)
        log("Phase 4", "HTTP server running")

        # ── Phase 5: Perform OTA Update ──────────────────────────────────
        ota_url = f"http://{local_ip}:{HTTP_PORT}/{fw_name}"
        url_len = len(ota_url)
        log("Phase 5", f"OTA URL: {ota_url} ({url_len} bytes)")

        ota_start_time = datetime.now()
        log("Phase 5", f"OTA begin: {ota_start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        ota_started = False
        for attempt in range(3):
            log("Phase 5", f"Sending AT+USEROTA={url_len} (attempt {attempt + 1})")
            resp = send_at(ser, f"AT+USEROTA={url_len}", timeout=AT_TIMEOUT, expect=">")
            if ">" in resp:
                ota_started = True
                break
            if "ERROR" in resp:
                log("Phase 5", "Got ERROR, clearing with AT...")
                send_at(ser, "AT")
                time.sleep(1)

        if not ota_started:
            log("Phase 5", "ERROR: Could not start OTA transfer.")
            log("Phase 5", "The ESP32 firmware may be too old to support OTA updates.")
            log("Phase 5", "You will need to update using a full serial flash with the")
            log("Phase 5", "factory image (factory_WROOM-32.bin). See FLASH_QUICK_START.txt.")
            raise SystemExit(1)

        log("Phase 5", f"Got > prompt, sending URL: {ota_url}")
        # Send URL with small inter-character delay — the Propeller
        # pass-through bridge may need time to shuttle bytes
        for ch in ota_url:
            ser.write(ch.encode("ascii"))
            time.sleep(0.01)
        time.sleep(0.5)

        log("Phase 5", "OTA transfer in progress...")
        last_pct = ""
        deadline = time.time() + OTA_TIMEOUT
        ota_complete = False
        reboot_detected = False
        ser.timeout = 2

        while time.time() < deadline:
            chunk = ser.read(ser.in_waiting or 1)
            if chunk:
                text = chunk.decode("ascii", errors="replace")
                # Show raw serial data
                sys.stdout.write(text)
                sys.stdout.flush()
                # Look for progress percentages (some firmware versions report them)
                pct_matches = re.findall(r'(\d+\.\d+)%', text)
                for pct in pct_matches:
                    if pct != last_pct:
                        last_pct = pct
                if "100.0%" in text:
                    ota_complete = True
                # Some firmware skips progress, goes straight to WIFI DISCONNECT
                if "WIFI DISCONNECT" in text and not reboot_detected:
                    log("Phase 5", "\nWIFI DISCONNECT — OTA transfer done, ESP32 rebooting...")
                    ota_complete = True
                # Reboot detected
                if "rst:0x" in text or "boot:" in text:
                    reboot_detected = True
                    ota_complete = True
                # Propeller re-init after reboot — definitive success
                if reboot_detected and "ready" in text:
                    print()
                    ota_end_time = datetime.now()
                    ota_elapsed = (ota_end_time - ota_start_time).total_seconds()
                    log("Phase 5", f"OTA complete — ESP32 rebooted and re-initialized")
                    log("Phase 5", f"OTA finished: {ota_end_time.strftime('%Y-%m-%d %H:%M:%S')}  (elapsed: {ota_elapsed:.1f}s)")
                    break
            else:
                time.sleep(0.1)

        if not ota_complete:
            log("Phase 5", "ERROR: OTA did not reach 100% within timeout")
            raise SystemExit(1)

        if ota_complete and not reboot_detected:
            # Got 100% or DISCONNECT but missed the reboot messages
            # Just wait for reboot to finish
            ota_end_time = datetime.now()
            ota_elapsed = (ota_end_time - ota_start_time).total_seconds()
            log("Phase 5", f"OTA finished: {ota_end_time.strftime('%Y-%m-%d %H:%M:%S')}  (elapsed: {ota_elapsed:.1f}s)")
            log("Phase 5", "Waiting for ESP32 reboot to complete...")

        # ── Wait for reboot ──────────────────────────────────────────────
        log("Phase 5", f"Waiting {REBOOT_WAIT}s for ESP32 to reboot...")
        time.sleep(REBOOT_WAIT)
        ser.reset_input_buffer()

        # In AP mode, verify the PC has reconnected to the PMC8 AP network
        ap_reconnected = True
        if ap_mode:
            ap_ip = detect_ap_mode()
            if ap_ip == PMC8_AP_EXPECTED_PC_IP:
                log("Phase 5", f"PC reconnected to PMC8 AP ({ap_ip})")
            else:
                log("Phase 5", "PC has not reconnected to the PMC8 WiFi network.")
                log("Phase 5", f"Please ensure your PC is connected to the PMC8 WiFi")
                log("Phase 5", f"and has IP {PMC8_AP_EXPECTED_PC_IP}, then press Enter.")
                input()
                ap_ip = detect_ap_mode()
                if ap_ip == PMC8_AP_EXPECTED_PC_IP:
                    log("Phase 5", f"PC reconnected to PMC8 AP ({ap_ip})")
                else:
                    ap_reconnected = False
                    log("Phase 5", f"WARNING: PC is at {ap_ip or 'unknown'}, expected {PMC8_AP_EXPECTED_PC_IP}")
                    log("Phase 5", "WiFi verification will be skipped, but serial verification continues.")

        # ── Phase 6: Verify Update ───────────────────────────────────────
        log("Phase 6", "Verifying firmware update")

        # May need to re-enter pass-through if it was lost
        ok_received = False
        for attempt in range(3):
            resp = send_at(ser, "AT")
            if "OK" in resp:
                ok_received = True
                break
            time.sleep(1)

        if not ok_received:
            log("Phase 6", "Pass-through may have been lost, re-entering...")
            in_passthrough = False
            send_es(ser, "ESPw42!")
            time.sleep(1)
            in_passthrough = True
            for attempt in range(3):
                resp = send_at(ser, "AT")
                if "OK" in resp:
                    ok_received = True
                    break
                time.sleep(1)

        if not ok_received:
            log("Phase 6", "ERROR: ESP32 not responding after OTA reboot")
            raise SystemExit(1)

        resp = send_at(ser, "AT+GMR", timeout=AT_TIMEOUT, expect="OK")
        log("Phase 6", f"Firmware version info:\n{resp}")

        bin_match = re.search(r'Bin version[:\s]*(.*)', resp)
        new_version = bin_match.group(1).strip() if bin_match else "unknown"
        if bin_match:
            log("Phase 6", f"Bin version: {new_version}")

        # If AP mode and WiFi reconnect failed, use version comparison as fallback
        if ap_mode and not ap_reconnected:
            if new_version != old_version:
                log("Phase 6", f"Firmware changed: {old_version} -> {new_version}")
                print()
                confirm = input(f"New firmware version is {new_version}. Is this what you expected? (y/n): ").strip().lower()
                if confirm == "y":
                    # Skip Phases 7-9, go straight to success
                    log("Phase 8", "Exiting pass-through mode")
                    ser.write(b"###")
                    time.sleep(1)
                    in_passthrough = False

                    print()
                    print("=" * 60)
                    print("  OTA UPDATE APPEARS SUCCESSFUL")
                    print("=" * 60)
                    print()
                    print(f"  Previous firmware: {old_version}")
                    print(f"  New firmware:      {new_version}")
                    print(f"  Mode: DIRECT (AP)")
                    print()
                    print("WiFi bridge verification was skipped (PC could not reconnect).")
                    print("The ESP32 is already in AP mode — ready to use.")
                    print()
                    raise SystemExit(0)
                else:
                    log("Phase 6", "User reports unexpected version.")
                    log("Phase 6", "Try again, or use LAN mode (connect both PC and PMC8 to home WiFi).")
                    raise SystemExit(1)
            else:
                log("Phase 6", f"WARNING: Firmware version unchanged ({old_version}).")
                log("Phase 6", "OTA may have failed. Try again, or use LAN mode")
                log("Phase 6", "(connect both PC and PMC8 to home WiFi).")
                raise SystemExit(1)

        # ── Phase 7: Reconnect ESP32 to Home WiFi (LAN mode only) ─────
        if ap_mode:
            log("Phase 7", "DIRECT mode — skipping WiFi rejoin (ESP32 rebooted to AP mode)")
            esp_ip = PMC8_AP_IP
        else:
            log("Phase 7", "Reconnecting ESP32 to home WiFi")

            log("Phase 7", "Sending ATE0 (disable echo)...")
            send_at(ser, "ATE0")
            time.sleep(0.3)

            log("Phase 7", "Sending AT+CWMODE=1 (station mode)...")
            resp = send_at(ser, "AT+CWMODE=1")
            log("Phase 7", f"Response: {resp.strip()}")
            time.sleep(0.5)

            log("Phase 7", f'Sending AT+CWJAP="{ssid}","****" (joining network)...')
            resp = send_at(ser, f'AT+CWJAP="{ssid}","{password}"',
                            timeout=WIFI_JOIN_TIMEOUT, expect="GOT IP")
            log("Phase 7", f"Response: {resp.strip()}")

            esp_ip = None
            if "GOT IP" in resp:
                time.sleep(3)
                ser.reset_input_buffer()

                log("Phase 7", "Sending AT+CIPSTA? (query IP address)...")
                resp = send_at(ser, "AT+CIPSTA?", expect="OK")
                log("Phase 7", f"Response: {resp.strip()}")
                ip_match = re.search(r'ip:"([^"]+)"', resp)
                if ip_match:
                    esp_ip = ip_match.group(1)
                    log("Phase 7", f"ESP32 IP: {esp_ip}")

                # Re-establish TCP server so the HTTP bridge can reach the PMC8
                log("Phase 7", "Sending AT+CIPMUX=1 (enable multiple connections)...")
                resp = send_at(ser, "AT+CIPMUX=1")
                log("Phase 7", f"Response: {resp.strip()}")
                time.sleep(0.3)

                log("Phase 7", "Sending AT+CIPSERVER=1,54372 (start TCP server)...")
                resp = send_at(ser, "AT+CIPSERVER=1,54372")
                log("Phase 7", f"Response: {resp.strip()}")
                time.sleep(0.5)
            else:
                log("Phase 7", "WARNING: Could not rejoin WiFi, skipping bridge test")

        # ── Phase 8: Exit Pass-Through & Verify PMC8 ────────────────────
        log("Phase 8", "Exiting pass-through mode")
        ser.write(b"###")
        time.sleep(1)
        in_passthrough = False
        ser.reset_input_buffer()

        resp = send_es(ser, "ESGp0!")
        if "!" in resp:
            log("Phase 8", f"PMC8 responding: {resp.strip()}")
        else:
            log("Phase 8", f"WARNING: PMC8 did not respond to ESGp0! Got: {resp}")

        # Query PMC8 Propeller firmware version
        log("Phase 8", "Querying PMC8 firmware version (ESGv!)...")
        ver_resp = send_es(ser, "ESGv!")
        log("Phase 8", f"ESGv! response: {ver_resp.strip()}")
        pmc8_version, pmc8_compatible = check_pmc8_version(ver_resp)
        if pmc8_version:
            log("Phase 8", f"PMC8 Propeller firmware: {pmc8_version}")

        # ── Phase 9: Verify HTTP Bridge ──────────────────────────────────
        if not pmc8_compatible:
            log("Phase 9", f"Skipped — PMC8 firmware {pmc8_version or 'unknown'} is older than 20A02.1.8.2")
            log("Phase 9", "HTTP bridge requires Propeller firmware 20A02.1.8.2 or newer.")
        elif esp_ip:
            log("Phase 9", f"Testing HTTP bridge at {esp_ip}")
            time.sleep(2)
            bridge_resp = verify_http_bridge(esp_ip)
            log("Phase 9", f"HTTP bridge response: {bridge_resp.strip()}")
            if "ESGv" in bridge_resp:
                log("Phase 9", "HTTP bridge verified OK")
            elif "503" in bridge_resp:
                log("Phase 9", "Bridge responding (503 — TCP server not active in station mode, expected)")
            else:
                log("Phase 9", "WARNING: Unexpected bridge response")
        else:
            log("Phase 9", "Skipped — no ESP32 IP available")

        # ── Success ──────────────────────────────────────────────────────
        print()
        print("=" * 60)
        print("  OTA UPDATE COMPLETE")
        print("=" * 60)
        print()
        print(f"  Previous firmware: {old_version}")
        print(f"  New firmware:      {new_version}")
        print(f"  PMC8 responded: {resp.strip()}" if "!" in resp else "")
        if ap_mode:
            print(f"  Mode: DIRECT (AP) — ESP32 is back at {PMC8_AP_IP}")
        else:
            print("  Mode: LAN")
        print()
        if pmc8_version:
            print(f"  PMC8 Propeller firmware: {pmc8_version}")
        if ap_mode:
            print("The ESP32 is already in AP mode — ready to use.")
        else:
            print("The ESP32 will return to AP mode on next PMC8 power cycle.")
        print()
        if pmc8_version and not pmc8_compatible:
            print("NOTE: PMC8 Propeller firmware %s is older than 20A02.1.8.2." % pmc8_version)
            print("To use ExplorestarsLite direct-to-PMC8 via the HTTP bridge,")
            print("update the Propeller firmware to 20A02.1.8.2 or newer.")
            print()

    except SystemExit:
        pass
    except KeyboardInterrupt:
        print("\nAborted by user.")
        print("The PMC8 is safe — if the OTA was not completed, the previous")
        print("firmware is still intact. Power cycle the PMC8 and try again.")
    except Exception as e:
        log("ERROR", f"Unexpected error: {e}")
        print()
        print("The PMC8 is safe — if the update did not complete, the previous")
        print("firmware is still intact. Power cycle the PMC8 and try again.")
    finally:
        # ── Cleanup ──────────────────────────────────────────────────────
        if in_passthrough and ser and ser.is_open:
            log("Cleanup", "Exiting pass-through mode")
            ser.write(b"###")
            time.sleep(0.5)

        if httpd:
            log("Cleanup", "Stopping HTTP server")
            httpd.shutdown()

        if firewall_added:
            log("Cleanup", "Removing firewall rule")
            remove_firewall_rule()

        if ser and ser.is_open:
            ser.close()

        log("Cleanup", "Done")


if __name__ == "__main__":
    main()
