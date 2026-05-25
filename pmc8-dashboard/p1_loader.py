#!/usr/bin/env python3
"""
p1_loader.py — Propeller P1 boot-protocol loader (pure Python).

Python port of the Propeller P1 boot protocol logic from `p1load` by dbetz
(https://github.com/dbetz/p1load), MIT-licensed (c) 2015 dbetz. This module is
a derivative work re-implementing the documented protocol for direct in-process
use; the original MIT notice is reproduced in THIRD_PARTY_NOTICES.md.

It is a 1:1 port of the project's hardware-validated VB.NET implementation
(Pmc8FirmwareLoader.vb). No GPL code, no external binaries, and no Parallax
tools are involved.

What it does: opens a serial port to the PMC-Eight, pulses DTR to reset the
Propeller P1, performs the LFSR handshake, transmits a .binary firmware image,
and (for EEPROM modes) waits for the boot ROM's EEPROM write + verify
acknowledgements.

Public API (kept compatible with the previous uploader module):
    LoaderError                     -- raised on any protocol/IO failure
    upload(port, file_path, ...)    -- convenience wrapper
"""

import time

try:
    import serial
except ImportError:  # pragma: no cover - environment guard
    raise ImportError(
        "p1_loader requires the 'serial' module (pyserial).\n"
        "Install with: pip install pyserial"
    )


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
_ACK_TIMEOUT_S = 0.025          # per-attempt ACK timeout
_CHECKSUM_TIMEOUT_S = 10.0
_EEPROM_PROGRAM_TIMEOUT_S = 5.0
_EEPROM_VERIFY_TIMEOUT_S = 2.0
_HUB_MEMORY_SIZE = 32768
_LFSR_SEED = 0x50               # 'P'


def _noop(_msg):
    pass


class Pmc8FirmwareLoader:
    """In-process Propeller P1 loader over a serial port."""

    def __init__(self, port_name, progress=None):
        self._progress = progress if progress is not None else _noop
        self._txbuf = bytearray()
        self._lfsr = 0
        self._port = serial.Serial()
        self._port.port = port_name
        self._port.baudrate = _BAUD
        self._port.bytesize = serial.EIGHTBITS
        self._port.parity = serial.PARITY_NONE
        self._port.stopbits = serial.STOPBITS_ONE
        self._port.timeout = 0.2
        self._port.write_timeout = 5.0
        # Mirror the VB loader: assert neither line at open time.
        self._port.dtr = False
        self._port.rts = False
        try:
            self._port.open()
        except serial.SerialException as exc:
            raise LoaderError(f"Could not open serial port {port_name}: {exc}")

    # -- lifecycle ----------------------------------------------------------
    def close(self):
        if self._port is not None and self._port.is_open:
            try:
                self._port.close()
            except Exception:
                pass  # swallow on shutdown

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
        if image is None:
            raise LoaderError("Image is null")
        if len(image) == 0:
            raise LoaderError("Image is empty")
        if len(image) & 3:
            raise LoaderError(
                f"Image size must be a multiple of 4 (got {len(image)})"
            )
        if len(image) > _HUB_MEMORY_SIZE:
            raise LoaderError(
                f"Image too big for hub memory: {len(image)} > {_HUB_MEMORY_SIZE}"
            )

        self._report("HANDSHAKE")
        self._reset_propeller()
        self._send_handshake_pattern()

        self._report("RESPONSE")
        self._verify_handshake_response()

        self._report("VERSION")
        version = self._receive_version()
        self._report(f"Propeller version {version}")

        self._report(f"PROGRAM {len(image)} bytes ({len(image) // 4} longs)")
        self._send_long(kind)
        self._send_long(len(image) // 4)
        for i in range(0, len(image), 4):
            word = (
                image[i]
                | (image[i + 1] << 8)
                | (image[i + 2] << 16)
                | (image[i + 3] << 24)
            )
            self._send_long(word)
        self._flush_tx()

        # Boot-ROM checksum / RAM-load ACK.
        if not self._wait_for_ack(
            int(_CHECKSUM_TIMEOUT_S / _ACK_TIMEOUT_S), "RAM-load"
        ):
            raise LoaderError(
                "Boot ROM did not acknowledge RAM load (checksum failure or no chip)"
            )

        if kind in (EEPROM, EEPROM_RUN):
            self._report("EEPROM_WRITE")
            if not self._wait_for_ack(
                int(_EEPROM_PROGRAM_TIMEOUT_S / _ACK_TIMEOUT_S), "EEPROM write"
            ):
                raise LoaderError("EEPROM write ACK timed out or NAK")

            self._report("EEPROM_VERIFY")
            if not self._wait_for_ack(
                int(_EEPROM_VERIFY_TIMEOUT_S / _ACK_TIMEOUT_S), "EEPROM verify"
            ):
                raise LoaderError("EEPROM verify ACK timed out or NAK")

        self._report("DONE")
        return version

    # -- protocol -----------------------------------------------------------
    def _reset_propeller(self):
        # Pulse DTR high then low. The USB-serial chip's DTR signal is wired
        # (usually through an inverter) to the Propeller's RESn pin, so
        # asserting DTR holds the chip in reset.
        self._port.dtr = True
        time.sleep(_RESET_PULSE_S)
        self._port.dtr = False
        time.sleep(_POST_RESET_S)
        self._port.reset_input_buffer()
        self._port.reset_output_buffer()

    def _send_handshake_pattern(self):
        # Calibration pulse (1 byte = 1 bit time at this encoding).
        self._tx(0xF9)
        # 250 LFSR-driven bits; each carries one bit in bit0 and 0xFE marker.
        self._lfsr = _LFSR_SEED
        for _ in range(250):
            bit = self._iterate_lfsr()
            self._tx(bit | 0xFE)
        # 250 + 8 calibration bytes to clock out the echoed handshake (250
        # bits) plus the 8 chip-version bits.
        for _ in range(250 + 8):
            self._tx(0xF9)
        self._flush_tx()

    def _verify_handshake_response(self):
        # IMPORTANT: do NOT reset the LFSR here. Its state must continue from
        # where _send_handshake_pattern left it (after 250 iterations). The
        # boot ROM echoes back LFSR positions 250..499 as proof it knows the
        # same LFSR algorithm — a bidirectional handshake.
        for i in range(250):
            b = self._receive_bit(0.100)
            if b < 0:
                raise LoaderError(f"Handshake response timed out at bit {i}")
            expected = self._iterate_lfsr()
            if b != expected:
                raise LoaderError(
                    f"Handshake mismatch at bit {i}: got {b} expected {expected}"
                )

    def _receive_version(self):
        v = 0
        for i in range(8):
            b = self._receive_bit(0.050)
            if b < 0:
                raise LoaderError(f"Version receive timed out at bit {i}")
            v = ((v >> 1) & 0x7F) | (b << 7)
        return v

    def _receive_bit(self, timeout_s):
        # Read one byte; valid values are 0xFE (bit=0) or 0xFF (bit=1). Any
        # other byte is a checksum error — loop and read another. Returns -1
        # on timeout.
        deadline = time.monotonic() + timeout_s
        self._port.timeout = max(0.001, timeout_s)
        while True:
            data = self._port.read(1)
            if not data:
                return -1
            r = data[0] - 0xFE
            if (r & 0xFE) == 0:
                return r
            # otherwise garbage byte — keep reading until timeout
            if time.monotonic() >= deadline:
                return -1

    def _send_long(self, value):
        x = value & 0xFFFFFFFF
        for i in range(11):
            flag = 0x60 if i == 10 else 0
            b = (
                0x92
                | flag
                | (x & 1)
                | ((x & 2) << 2)
                | ((x & 4) << 4)
            ) & 0xFF
            self._tx(b)
            x >>= 3

    def _wait_for_ack(self, retries, _phase):
        for _ in range(retries):
            time.sleep(0.020)
            self._tx(0xF9)
            self._flush_tx()
            self._port.timeout = _ACK_TIMEOUT_S
            data = self._port.read(1)
            if data:
                # Per the p1load reference, ACK = 0xFE (bit=0), NAK = 0xFF.
                return data[0] == 0xFE
            # timeout — keep retrying
        return False

    def _tx(self, b):
        self._txbuf.append(b & 0xFF)
        # Flush periodically so the OS write buffer doesn't grow unbounded.
        if len(self._txbuf) >= 4096:
            self._flush_tx()

    def _flush_tx(self):
        if not self._txbuf:
            return
        self._port.write(bytes(self._txbuf))
        self._txbuf.clear()

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
