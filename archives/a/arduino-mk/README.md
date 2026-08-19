# arduino-mk (Arduino-Makefile)

Arduino-Makefile is a collection of Makefile include files (`.mk`) and Python utility scripts that allow you to compile and upload Arduino sketches from the command line, without the Arduino IDE.

## Installed Components

- `share/arduino/Arduino.mk` — main Makefile include
- `share/arduino/Common.mk` — common definitions
- `share/arduino/OpenCM.mk` — OpenCM board support
- `share/arduino/Teensy.mk` — Teensy board support
- `share/arduino/chipKIT.mk` — chipKIT board support
- `share/arduino/arduino-mk-vars.md` — variable documentation
- `bin/ard-reset-arduino` — Python script to reset Arduino boards (requires pySerial)
- `bin/robotis-loader` — Python script to upload firmware to Robotis boards (requires pySerial)
- `share/man/man1/` — man pages for the scripts
- `share/doc/arduino-mk/examples/` — example Arduino sketches

## Dependencies

- Python 3 (for ard-reset-arduino and robotis-loader scripts)
- pySerial (Python package, install via `pip install pyserial`)
- Arduino IDE (for the avr-gcc compiler and Arduino core libraries)

## Versions

| Version | Status | Date |
|---------|--------|------|
| 1.6.0 | built | 2026-08-07 |
