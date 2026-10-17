# minipro

Open source program for controlling XGecu's series of chip programmers.

## Description

Minipro is an open source command-line tool for controlling XGecu's TL866CS,
TL866A, TL866II+, T48, and T56 chip programmers. It provides a simple CLI
interface for reading, writing, and verifying EEPROMs, microcontrollers, and
other programmable devices.

## Features

- Native support for Linux, BSD, macOS, and other Unix flavors
- Compatibility with TL866CS, TL866A, TL866II+, T48, and T56 from XGecu
- More than 13000 target devices (AVRs, PICs, BIOSes, EEPROMs)
- ZIF40 socket and ISP support
- Vendor-specific MCU configuration bits
- Chip ID verification
- Logic IC testing
- Bitbang support
- Overcurrent protection

## Usage

```bash
# Read a chip
minipro -p ATMEGA48 -r atmega48.bin

# Write a chip
minipro -p ATMEGA48 -w atmega48.bin
```

## Versions

- 0.7.4 (2026-07-16) - Built for OpenHarmony aarch64

## Links

- GitLab: https://gitlab.com/DavidGriffith/minipro
