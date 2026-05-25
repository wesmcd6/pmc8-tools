#!/usr/bin/env python3
"""
p1_loader.py - Propeller P1 boot-protocol loader (pure Python).

Derived from `p1load` (https://github.com/dbetz/p1load), MIT-licensed. Both
sources below are MIT; this module is offered under the same MIT terms and the
original notices are reproduced in THIRD_PARTY_NOTICES.md:
  - boot protocol (handshake/version/encoding/ACK) ported from ploader.c,
    Copyright (c) 2015 dbetz (adapted from Chip Gracey's PNut IDE);
  - Windows raw-Win32 serial transport mirrors osint_mingw.c,
    Copyright (c) 2011 by Steve Denson.
No GPL code, no external binaries, and no Parallax tools.

What it does: opens the serial port to the PMC-Eight, pulses DTR to reset the
Propeller P1, performs the LFSR handshake, transmits a .binary firmware image
in one contiguous write, and (for EEPROM modes) waits for the boot ROM's EEPROM
write + verify acknowledgements.

IMPORTANT (Windows): the program image must be transmitted as one contiguous
stream. pyserial on Windows uses overlapped WriteFile, which leaves inter-byte
gaps mid-image that trip the boot ROM's download timeout (it then aborts and
boots from EEPROM). So on Windows we talk to the port through raw Win32 calls
(ctypes) with a synchronous WriteFile, exactly as p1load's osint_mingw.c does.
On other platforms pyserial's synchronous write is fine.

Public API (kept compatible with the previous uploader module):
    LoaderError                     -- raised on any protocol/IO failure
    upload(port, file_path, ...)    -- convenience wrapper
"""

import sys
import time


# ---- load types ------------------------------------------------------------
SHUTDOWN = 0       # load to RAM, stop (Propeller goes to sleep)
RUN_FROM_RAM = 1   # load to RAM, run immediately
EEPROM = 2         # write to EEPROM, stop
EEPROM_RUN = 3     # write to EEPROM, then run from RAM


class LoaderError(Exception):
    """Raised on any Propeller load protocol or serial-IO failure."""


# ---- wire constants — from ploader.h / Chip Gracey's PNut IDE --------------
_BAUD = 115200
_RESET_PULSE_S = 0.025          # DTR pulse width holding RST asserted
_POST_RESET_S = 0.090           # boot ROM startup wait
_ACK_TIMEOUT_MS = 25            # per-attempt ACK timeout
_CHECKSUM_TIMEOUT_MS = 10000    # big: includes whole program-load time
_EEPROM_PROGRAM_TIMEOUT_MS = 5000
_EEPROM_VERIFY_TIMEOUT_MS = 2000
_HUB_MEMORY_SIZE = 32768
_LFSR_SEED = 0x50               # 'P'


def _noop(_msg):
    pass


# ======================================================================
#  Transports — each exposes: reset(), tx(bytes), rx_timeout(n, ms)->bytes,
#  close().  rx_timeout returns up to n bytes, or b"" on timeout.
# ======================================================================

class _Win32Transport:
    """Raw Win32 serial transport (ctypes). Mirrors p1load's osint_mingw.c:
    synchronous, non-overlapped WriteFile so the firmware image streams as one
    uninterrupted block."""

    def __init__(self, port_name):
        import ctypes
        from ctypes import wintypes
        self._ctypes = ctypes
        self._k32 = ctypes.WinDLL("kernel32", use_last_error=True)

        GENERIC_READ = 0x80000000
        GENERIC_WRITE = 0x40000000
        OPEN_EXISTING = 3
        INVALID = ctypes.c_void_p(-1).value
        self._MAXDWORD = 0xFFFFFFFF
        self._PURGE_ALL = 0x0F

        class DCB(ctypes.Structure):
            _fields_ = [
                ("DCBlength", wintypes.DWORD), ("BaudRate", wintypes.DWORD),
                ("fBinary", wintypes.DWORD, 1), ("fParity", wintypes.DWORD, 1),
                ("fOutxCtsFlow", wintypes.DWORD, 1), ("fOutxDsrFlow", wintypes.DWORD, 1),
                ("fDtrControl", wintypes.DWORD, 2), ("fDsrSensitivity", wintypes.DWORD, 1),
                ("fTXContinueOnXoff", wintypes.DWORD, 1), ("fOutX", wintypes.DWORD, 1),
                ("fInX", wintypes.DWORD, 1), ("fErrorChar", wintypes.DWORD, 1),
                ("fNull", wintypes.DWORD, 1), ("fRtsControl", wintypes.DWORD, 2),
                ("fAbortOnError", wintypes.DWORD, 1), ("fDummy2", wintypes.DWORD, 17),
                ("wReserved", wintypes.WORD), ("XonLim", wintypes.WORD),
                ("XoffLim", wintypes.WORD), ("ByteSize", wintypes.BYTE),
                ("Parity", wintypes.BYTE), ("StopBits", wintypes.BYTE),
                ("XonChar", ctypes.c_char), ("XoffChar", ctypes.c_char),
                ("ErrorChar", ctypes.c_char), ("EofChar", ctypes.c_char),
                ("EvtChar", ctypes.c_char), ("wReserved1", wintypes.WORD),
            ]

        class TIMEOUTS(ctypes.Structure):
            _fields_ = [
                ("ReadIntervalTimeout", wintypes.DWORD),
                ("ReadTotalTimeoutMultiplier", wintypes.DWORD),
                ("ReadTotalTimeoutConstant", wintypes.DWORD),
                ("WriteTotalTimeoutMultiplier", wintypes.DWORD),
                ("WriteTotalTimeoutConstant", wintypes.DWORD),
            ]

        self._TIMEOUTS = TIMEOUTS
        self._SETDTR, self._CLRDTR = 5, 6

        handle = self._k32.CreateFileW(
            f"\\\\.\\{port_name}", GENERIC_READ | GENERIC_WRITE,
            0, None, OPEN_EXISTING, 0, None)
        if handle == INVALID:
            raise LoaderError(
                f"Could not open serial port {port_name} "
                f"(Win32 error {ctypes.get_last_error()})")
        self._h = wintypes.HANDLE(handle)

        try:
            dcb = DCB()
            dcb.DCBlength = ctypes.sizeof(DCB)
            self._must(self._k32.GetCommState(self._h, ctypes.byref(dcb)),
                       "GetCommState")
            dcb.BaudRate = _BAUD
            dcb.ByteSize = 8
            dcb.Parity = 0          # NOPARITY
            dcb.StopBits = 0        # ONESTOPBIT
            dcb.fBinary = 1
            dcb.fParity = 0
            dcb.fOutxCtsFlow = 0
            dcb.fOutxDsrFlow = 0
            dcb.fDtrControl = 0     # DTR_CONTROL_DISABLE
            dcb.fRtsControl = 0     # RTS_CONTROL_DISABLE
            dcb.fDsrSensitivity = 0
            dcb.fInX = 0
            dcb.fOutX = 0
            dcb.fTXContinueOnXoff = 1
            dcb.fNull = 0
            dcb.fAbortOnError = 0
            self._must(self._k32.SetCommState(self._h, ctypes.byref(dcb)),
                       "SetCommState")

            self._to = TIMEOUTS()
            self._must(self._k32.GetCommTimeouts(self._h, ctypes.byref(self._to)),
                       "GetCommTimeouts")
            self._to.ReadIntervalTimeout = self._MAXDWORD
            self._to.ReadTotalTimeoutMultiplier = self._MAXDWORD
            self._must(self._k32.SetupComm(self._h, 10000, 10000), "SetupComm")
            self._k32.PurgeComm(self._h, self._PURGE_ALL)
        except Exception:
            self.close()
            raise

    def _must(self, ok, name):
        if not ok:
            raise LoaderError(
                f"{name} failed (Win32 error {self._ctypes.get_last_error()})")

    def reset(self):
        self._k32.EscapeCommFunction(self._h, self._SETDTR)
        time.sleep(_RESET_PULSE_S)
        self._k32.EscapeCommFunction(self._h, self._CLRDTR)
        time.sleep(_POST_RESET_S)
        self._k32.PurgeComm(self._h, self._PURGE_ALL)

    def tx(self, data):
        from ctypes import wintypes, byref
        n = wintypes.DWORD(0)
        self._must(self._k32.WriteFile(self._h, data, len(data), byref(n), None),
                   "WriteFile")
        return n.value

    def rx_timeout(self, nbytes, timeout_ms):
        from ctypes import byref
        self._to.ReadTotalTimeoutConstant = timeout_ms
        self._k32.SetCommTimeouts(self._h, byref(self._to))
        buf = (self._ctypes.c_ubyte * nbytes)()
        from ctypes import wintypes
        n = wintypes.DWORD(0)
        self._must(self._k32.ReadFile(self._h, buf, nbytes, byref(n), None),
                   "ReadFile")
        return bytes(buf[:n.value])

    def close(self):
        if getattr(self, "_h", None):
            self._k32.CloseHandle(self._h)
            self._h = None


class _PySerialTransport:
    """pyserial transport for non-Windows platforms (Linux). pyserial's POSIX
    write() is synchronous, so the image streams contiguously without the
    overlapped-write gaps seen on Windows."""

    def __init__(self, port_name):
        try:
            import serial
        except ImportError:
            raise LoaderError(
                "p1_loader requires the 'serial' module (pyserial) on this "
                "platform.\nInstall with: pip install pyserial")
        self._serial = serial
        port = serial.Serial()
        port.port = port_name
        port.baudrate = _BAUD
        port.bytesize = serial.EIGHTBITS
        port.parity = serial.PARITY_NONE
        port.stopbits = serial.STOPBITS_ONE
        port.timeout = 0.2
        port.write_timeout = 30.0
        port.dtr = False
        port.rts = False
        try:
            port.open()
        except serial.SerialException as exc:
            raise LoaderError(f"Could not open serial port {port_name}: {exc}")
        self._port = port

    def reset(self):
        self._port.dtr = True
        time.sleep(_RESET_PULSE_S)
        self._port.dtr = False
        time.sleep(_POST_RESET_S)
        self._port.reset_input_buffer()
        self._port.reset_output_buffer()

    def tx(self, data):
        return self._port.write(data)

    def rx_timeout(self, nbytes, timeout_ms):
        self._port.timeout = max(0.001, timeout_ms / 1000.0)
        return self._port.read(nbytes)

    def close(self):
        port = getattr(self, "_port", None)
        if port is not None and port.is_open:
            try:
                port.close()
            except Exception:
                pass


def _open_transport(port_name):
    if sys.platform.startswith("win"):
        return _Win32Transport(port_name)
    return _PySerialTransport(port_name)


# ======================================================================
#  Loader protocol — mirrors p1load's ploader.c
# ======================================================================

class Pmc8FirmwareLoader:
    """In-process Propeller P1 loader over a serial transport."""

    def __init__(self, port_name, progress=None):
        self._progress = progress if progress is not None else _noop
        self._t = _open_transport(port_name)
        self._rxbuf = b""
        self._rxnext = 0
        self._lfsr = 0

    def close(self):
        if self._t is not None:
            self._t.close()
            self._t = None

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()

    # -- main entry ---------------------------------------------------------
    def load(self, image, kind):
        """Load `image` (bytes) into the Propeller using `kind` (load type).

        Returns the chip version reported by the handshake (1 for P1).
        Raises LoaderError on protocol failure.
        """
        if image is None or len(image) == 0:
            raise LoaderError("Image is empty")
        if len(image) & 3:
            raise LoaderError(
                f"Image size must be a multiple of 4 (got {len(image)})")
        if len(image) > _HUB_MEMORY_SIZE:
            raise LoaderError(
                f"Image too big for hub memory: {len(image)} > {_HUB_MEMORY_SIZE}")

        # Pre-encode the whole download payload so it goes out in one write().
        payload = bytearray()
        payload += self._encode_long(kind)
        payload += self._encode_long(len(image) // 4)
        for i in range(0, len(image), 4):
            word = (
                image[i]
                | (image[i + 1] << 8)
                | (image[i + 2] << 16)
                | (image[i + 3] << 24)
            )
            payload += self._encode_long(word)
        payload = bytes(payload)

        version = self._hardware_found()
        self._report(f"Propeller version {version}")

        self._report(f"PROGRAM {len(image)} bytes ({len(image) // 4} longs)")
        self._t.tx(payload)

        # Boot-ROM checksum / RAM-load ACK.
        sts = self._wait_for_ack(_CHECKSUM_TIMEOUT_MS // _ACK_TIMEOUT_MS)
        if sts < 0:
            raise LoaderError(
                "Boot ROM did not acknowledge RAM load (timeout or no chip)")
        if sts == 0:
            raise LoaderError("RAM load failed checksum (NAK)")

        if kind in (EEPROM, EEPROM_RUN):
            self._report("EEPROM_WRITE")
            sts = self._wait_for_ack(_EEPROM_PROGRAM_TIMEOUT_MS // _ACK_TIMEOUT_MS)
            if sts < 0:
                raise LoaderError("EEPROM write ACK timed out")
            if sts == 0:
                raise LoaderError("EEPROM write failed (NAK)")

            self._report("EEPROM_VERIFY")
            sts = self._wait_for_ack(_EEPROM_VERIFY_TIMEOUT_MS // _ACK_TIMEOUT_MS)
            if sts < 0:
                raise LoaderError("EEPROM verify ACK timed out")
            if sts == 0:
                raise LoaderError("EEPROM verify failed (NAK)")

        self._report("DONE")
        return version

    # -- handshake ----------------------------------------------------------
    def _hardware_found(self):
        self._rxbuf = b""
        self._rxnext = 0

        self._report("HANDSHAKE")
        self._t.reset()

        # Calibration pulse + 250 LFSR handshake bits + 258 clock-out pulses,
        # all in one buffer / one write.
        buf = bytearray()
        buf.append(0xF9)
        self._lfsr = _LFSR_SEED
        for _ in range(250):
            buf.append(self._iterate_lfsr() | 0xFE)
        for _ in range(250 + 8):
            buf.append(0xF9)
        self._t.tx(bytes(buf))

        self._report("RESPONSE")
        for i in range(250):
            bit = self._receive_bit(100)
            if bit < 0:
                raise LoaderError(f"Handshake response timed out at bit {i}")
            if bit != self._iterate_lfsr():
                raise LoaderError(f"Handshake mismatch at bit {i}")

        self._report("VERSION")
        version = 0
        for i in range(8):
            bit = self._receive_bit(50)
            if bit < 0:
                raise LoaderError(f"Version receive timed out at bit {i}")
            version = ((version >> 1) & 0x7F) | (bit << 7)
        return version

    def _wait_for_ack(self, retries):
        """Returns 1 (ACK), 0 (NAK/checksum fail), or -1 (timeout)."""
        for _ in range(retries):
            time.sleep(0.020)
            self._t.tx(b"\xf9")
            data = self._t.rx_timeout(1, _ACK_TIMEOUT_MS)
            if data:
                return 1 if data[0] == 0xFE else 0
        return -1

    # -- bit / long helpers (from ploader.c) --------------------------------
    def _receive_bit(self, timeout_ms):
        # Valid bytes are 0xFE (bit 0) / 0xFF (bit 1); any other byte is a
        # checksum error during the response — skip it. Returns -1 on timeout.
        while True:
            if self._rxnext >= len(self._rxbuf):
                self._rxbuf = self._t.rx_timeout(256, timeout_ms)
                self._rxnext = 0
                if not self._rxbuf:
                    return -1
            result = self._rxbuf[self._rxnext] - 0xFE
            self._rxnext += 1
            if (result & 0xFE) == 0:
                return result

    @staticmethod
    def _encode_long(value):
        """Encode a 32-bit value into the 11-byte Propeller download form."""
        x = value & 0xFFFFFFFF
        out = bytearray(11)
        for i in range(11):
            flag = 0x60 if i == 10 else 0
            out[i] = (
                0x92 | flag | (x & 1) | ((x & 2) << 2) | ((x & 4) << 4)
            ) & 0xFF
            x >>= 3
        return bytes(out)

    def _iterate_lfsr(self):
        # Same polynomial as the Propeller boot ROM (taps 7, 5, 4, 1).
        lfsr = self._lfsr
        result = lfsr & 1
        tap = ((lfsr >> 7) ^ (lfsr >> 5) ^ (lfsr >> 4) ^ (lfsr >> 1)) & 1
        self._lfsr = ((lfsr << 1) & 0xFE) | tap
        return result

    def _report(self, phase):
        self._progress(phase)


def upload(port, file_path, eeprom=True, run=True, gpio_pin=-1,
           progress=None, terminal=False):
    """Convenience wrapper matching the previous uploader's call signature.

    `gpio_pin` and `terminal` are accepted for compatibility but unused: this
    loader resets the Propeller via the serial DTR line only and does not open
    a post-upload terminal.
    """
    if gpio_pin is not None and gpio_pin >= 0 and progress is not None:
        progress("Note: GPIO reset is not supported; using serial DTR reset.")

    with open(file_path, "rb") as fh:
        image = fh.read()

    if eeprom and run:
        kind = EEPROM_RUN
    elif eeprom:
        kind = EEPROM
    elif run:
        kind = RUN_FROM_RAM
    else:
        kind = SHUTDOWN

    loader = Pmc8FirmwareLoader(port, progress=progress)
    try:
        return loader.load(image, kind)
    finally:
        loader.close()
