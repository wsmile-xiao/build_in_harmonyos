# libjaylink

libjaylink is a shared library written in C to access SEGGER J-Link and compatible devices.

## Description

libjaylink provides an API for communicating with SEGGER J-Link debug probes and compatible devices. It supports multiple transports:
- USB (via libusb-1.0)
- TCP/IP

## Features

- USB device discovery and enumeration
- JTAG and SWD protocol support
- Target memory access
- Flash programming support
- Multi-device support

## Dependencies

- libusb-1.0 >= 1.0.16 (optional, for USB transport)
- clang/gcc >= 4.0

## Available Versions

| Version | Status | Build Date | Notes |
|---------|--------|------------|-------|
| 0.2.0 | built | 2026-06-04 | [Details](./0.2.0/notes.md) |

## Usage

After installation, you can use libjaylink in your projects:

```bash
# pkg-config integration
pkg-config --cflags --libs libjaylink

# Example output:
# -I/path/to/include -L/path/to/lib -ljaylink
```

## License

GPL-2.0-or-later

## Homepage

- GitLab: https://gitlab.zapb.de/libjaylink/libjaylink
- GitHub Mirror: https://github.com/syntacore/libjaylink

## See Also

- OpenOCD (uses libjaylink for J-Link support)
- SEGGER J-Link software