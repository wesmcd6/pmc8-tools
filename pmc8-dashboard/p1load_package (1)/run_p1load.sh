
# Attribution Notice
echo ""
echo "This script utilizes 'p1load' by dbetz, licensed under the MIT License."
echo "Source: https://github.com/dbetz/p1load"
echo ""




#!/bin/bash

# Check if the firmware file argument is provided
if [ $# -ne 1 ]; then
  echo "Usage: $0 <firmware_file>"
  exit 1
fi

# Get the firmware file from the command-line argument
FIRMWARE_FILE="$1"

# Prompt the user for confirmation
echo "Will load firmware $FIRMWARE_FILE. Proceed? (Y/N)"
read -r response
if [[ "$response" != "Y" && "$response" != "y" ]]; then
  echo "Exiting without loading firmware."
  exit 0
fi

# Path to the p1load executable
P1LOAD="./p1load"  # Change this if p1load is located in a different directory

# Check if p1load exists and is executable
if [[ ! -x "$P1LOAD" ]]; then
  echo "Error: p1load executable not found or is not executable."
  exit 1
fi

# Detect the serial port automatically using p1load -P
SERIAL_PORT=$($P1LOAD -P | grep -o '/dev/cu.usbserial-[^ ]*')

# Check if a serial port was found
if [ -z "$SERIAL_PORT" ]; then
  echo "Error: No serial port detected. Please make sure the device is connected."
  exit 1
fi

# Run p1load with the detected serial port and firmware file
$P1LOAD -p $SERIAL_PORT -e $FIRMWARE_FILE -r

echo "PMC8 is booting...wait for status light"
echo ""
