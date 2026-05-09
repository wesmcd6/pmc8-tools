#!/usr/bin/env python
"""
Parallax Propeller Loader

Modified 2025 by Wes McDonald
Modified 2015 by Phil Howard
Original (C) 2007 Remy Blank

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License, version 2.
See http://www.gnu.org/licenses/gpl-2.0.html

This module provides a Loader class for uploading code to the Propeller chip,
and functions (upload, watch_upload, detect_port) that can be called by another
application (e.g. your PMC8 configurator).
"""

import glob
import os
import sys
import time

try:
    import serial
except ImportError:
    sys.exit("This library requires the serial module\nInstall with: sudo pip install pyserial")

from functools import reduce

# Processor constants
LFSR_REQUEST_LEN   = 250
LFSR_REPLY_LEN     = 250
LFSR_SEED          = ord("P")
CMD_SHUTDOWN       = 0
CMD_LOADRAMRUN     = 1
CMD_LOADEPPROM     = 2
CMD_LOADEPPROMRUN  = 3
EEPROM_SIZE        = 32768

# Platform defaults
defSerial = {
    "posix": "/dev/ttyUSB0",
    "nt": "COM1",
}

def do_nothing(msg):
    """Default progress callback that does nothing."""
    pass

def serial_ports():
    """Return a list of available serial ports."""
    if sys.platform.startswith('win'):
        ports = ['COM' + str(i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')
    result = []
    for port in ports:
        try:
            s = serial.Serial()
            s.port = port
            s.baudrate = 115200
            s.timeout = 0
            s.write_timeout = 1
            s.xonxoff = False
            s.rtscts = False
            s.dsrdtr = False
            s.dtr = False
            s.rts = False
            s.open()
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result

class LoaderError(Exception):
    pass

class Loader(object):
    print("Loader Script started")
    """Propeller code uploader."""
    
    def __init__(self, port, reset_gpio=-1):
        self.serial = serial.Serial(baudrate=115200, timeout=0)
        self.serial.port = port
        self.serial.write_timeout = 1
        self.serial.xonxoff = False
        self.serial.rtscts = False
        self.serial.dsrdtr = False
        self.serial.dtr = False
        self.serial.rts = False
        self.reset_gpio = reset_gpio
        self.gpio = None

        if self.reset_gpio > -1:
            try:
                import RPi.GPIO as GPIO
                self.gpio = GPIO
                self.gpio.setmode(GPIO.BCM)
                self.gpio.setwarnings(False)
                self.gpio.setup(self.reset_gpio, GPIO.OUT, initial=GPIO.HIGH)
            except ImportError:
                print("RPi.GPIO library required for GPIO reset.")

    def _cleanup(self):
        if self.serial.isOpen():
            self.serial.close()
        if self.reset_gpio > -1 and self.gpio is not None:
            self.gpio.cleanup()

    def __del__(self):
        self._cleanup()

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self._cleanup()
        
    def _lfsr(self, seed):
        """Generate bits from 8-bit LFSR."""
        while True:
            yield seed & 0x01
            seed = ((seed << 1) & 0xfe) | (((seed >> 7) ^ (seed >> 5) ^ (seed >> 4) ^ (seed >> 1)) & 1)

    # High-level functions
    def get_version(self, progress=do_nothing):
        """Connect to the Propeller and return its version."""
        self._open()
        try:
            version = self._connect()
            self._write_long(CMD_SHUTDOWN)
            time.sleep(0.1)
            self.reset()
            return version
        finally:
            self._close()
        
    def upload(self, code=None, path=None, eeprom=False, run=True, progress=do_nothing, terminal=False):
        """Connect to the Propeller and upload code to RAM or EEPROM."""
        if path is not None:
            with open(path, "rb") as f:
                code = f.read()
        self._open()
        try:
            code, code_len = self._prepare_code(code, eeprom)
            version = self._connect()
            progress("Connected (version={})".format(version))
            self._send_code(code, code_len, eeprom, run, progress)
        finally:
            if terminal:
                while True:
                    ser = self.serial.read()
                    if ser is not None:
                        sys.stdout.write(ser)
                        sys.stdout.flush()
            else:
                self._close()
    
    # Low-level functions

    def _open(self):
        if self.serial.isOpen():
            self.serial.close()  # Force close the port if itâ€™s open

        try:
            print(f"Opening serial port {self.serial.port} at {self.serial.baudrate} baud")
            self.serial.open()
        except OSError as e:
            raise LoaderError(str(e))






    
    def _close(self):
        self.serial.close()
        
    def reset(self):
        """Reset the Propeller."""
        self.serial.flushOutput()
        if self.reset_gpio > -1 and self.gpio is not None:
            self.gpio.output(self.reset_gpio, self.gpio.LOW)
            time.sleep(0.1)
            self.gpio.output(self.reset_gpio, self.gpio.HIGH)
            time.sleep(0.1)
        else:
            self.serial.setDTR(1)
            time.sleep(0.1)
            self.serial.setDTR(0)
            time.sleep(0.1)
        self.serial.flushInput()
        
    def _calibrate(self):
        """Send a calibration pulse to the Propeller."""
        self._write_byte(0xf9)
        
    def _connect(self):
        """Perform the LFSR handshake with the Propeller."""
        self.reset()
        self._calibrate()
        seq = []
    
        # Prime the LFSR sequence with 500 values.
        for (i, value) in zip(range(LFSR_REQUEST_LEN + LFSR_REPLY_LEN), self._lfsr(LFSR_SEED)):
            seq.append(value)

        self.serial.write(bytes([each | 0xfe for each in seq[0:LFSR_REQUEST_LEN]]))
        self.serial.write(bytes([0xf9] * (LFSR_REPLY_LEN + 8)))

        for i in range(LFSR_REQUEST_LEN, LFSR_REQUEST_LEN + LFSR_REPLY_LEN):
            if self._read_bit(False, 0.200) != seq[i]:
                raise LoaderError("No hardware found")

        version = 0
        for i in range(8):
            version = ((version >> 1) & 0x7f) | ((self._read_bit(False, 0.050) << 7))
        return version

    def _bin_to_eeprom(self, code):
        dbase = code[0x0a] + (code[0x0b] << 8)
        if len(code) > EEPROM_SIZE - 8:
            raise LoaderError("Code too long for EEPROM (max %d bytes)" % (EEPROM_SIZE - 8))
        if dbase > EEPROM_SIZE:
            raise LoaderError("Invalid binary format")
        code += bytes([0x00]) * (dbase - 8 - len(code))
        footer = bytes([0xff, 0xff, 0xf9, 0xff, 0xff, 0xff, 0xf9, 0xff])
        code += footer
        code += bytes([0x00]) * (EEPROM_SIZE - len(code))
        return code

    def _prepare_code(self, code, eeprom=False):
        if len(code) == 0:
            raise LoaderError("Empty file specified")
        if len(code) % 4 != 0:
            raise LoaderError("Invalid code size: must be a multiple of 4")
        if eeprom and len(code) < EEPROM_SIZE:
            code = self._bin_to_eeprom(code)

        checksum = sum(code)
        if not eeprom:
            checksum += 2 * (0xff + 0xff + 0xf9 + 0xff)
        checksum &= 0xff
        if checksum != 0:
            raise LoaderError("Code checksum error: 0x{:0>2x}".format(checksum))

        code_len = len(code)
        encoded_binary = b""
        for i in range(0, len(code), 4):
            encoded_chunk = self._encode_long(
                code[i] | (code[i+1] << 8) | (code[i+2] << 16) | (code[i+3] << 24))
            encoded_binary += encoded_chunk
        return encoded_binary, code_len
 
    def _send_code(self, encoded_code, code_length, eeprom=False, run=True, progress=do_nothing):
        command = eeprom * 2 + run
        self._write_long(command)
        if not eeprom and not run:
            return
        self._write_long(code_length // 4)
        progress("Sending code ({} bytes) Please Wait".format(code_length))
        self.serial.write(encoded_code)
        self.serial.flushInput()
        if self._read_bit(True, 12) == 1:
            raise LoaderError("RAM checksum error")
        if eeprom:
            progress("Programming EEPROM")
            if self._read_bit(True, 5) == 1:
                raise LoaderError("EEPROM programming error")
            progress("Verifying EEPROM")
            if self._read_bit(True, 2.5) == 1:
                raise LoaderError("EEPROM verification error")

    def _write_long(self, value):
        encoded_value = self._encode_long(value)
        self.serial.write(encoded_value)

    def _encode_long(self, value):
        result = []
        for i in range(10):
            result.append(0x92 | (value & 0x01) | ((value & 2) << 2) | ((value & 4) << 4))
            value >>= 3
        result.append(0xf2 | (value & 0x01) | ((value & 2) << 2))
        return bytes(result)

    def _write_byte(self, value):
        self.serial.write(bytes([value]))

    def _read_bit(self, echo, timeout):
        start = time.time()
        while time.time() - start < timeout:
            if echo:
                self._write_byte(0xf9)
                time.sleep(0.1)
            c = self.serial.read(1)
            if c:
                if c in (b'\xfe', b'\xff'):
                    return c[0] & 0x01
                else:
                    extra = self.serial.read(20)
                    full_response = c + extra
                    print("DEBUG: Unexpected byte received!: ", full_response)
                    raise LoaderError("Bad reply: " + repr(full_response))
        raise LoaderError("Timeout error")

def upload(serial_port, path, eeprom=False, run=True, gpio_pin=-1, progress=do_nothing, terminal=False):
    with Loader(serial_port, gpio_pin) as loader:
        progress("Uploading {}".format(path))
        loader.upload(path=path, eeprom=eeprom, run=run, progress=progress, terminal=terminal)
        progress("Done")

def watch_upload(serial_port, path, delay, eeprom=False, run=True, gpio_pin=-1, progress=do_nothing):
    upload(serial_port, path, eeprom, run, gpio_pin, progress)
    progress("\nEntering watch mode. ( Ctrl+C to quit )\n")
    mtime = os.stat(path).st_mtime
    while True:
        try:
            prevMTime = mtime
            try:
                mtime = os.stat(path).st_mtime
            except OSError:
                mtime = None
            if (mtime is not None) and (mtime != prevMTime):
                progress("File change detected")
                time.sleep(delay)
                upload(serial_port, path, eeprom, run, gpio_pin, progress)
                progress("\nResuming watch mode. ( Ctrl+C to quit )\n")
            else:
                time.sleep(1)
        except LoaderError as e:
            progress(str(e) + "\n")

def detect_port(gpio_pin=-1):
    for port in serial_ports():
        try:
            with Loader(port, gpio_pin) as loader:
                version = loader.get_version()
                if version > 0:
                    return (port, version)
        except LoaderError as e:
            continue
    return defSerial.get(os.name, "none")

# The command-line interface block has been removed so that this file
# can be imported as a module into your PMC8 configurator.

