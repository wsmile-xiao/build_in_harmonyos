# usbredir

USB redirection protocol library for Spice/QEMU.

## Description

usbredir is a protocol for redirection USB traffic from a single USB device to a different (virtual) machine. This package provides:

- **libusbredirparser**: Library for parsing the usbredir protocol
- **libusbredirhost**: Library implementing the usb-host side of a usbredir connection
- **usbredirect**: Tool for USB device redirection over TCP

## Dependencies

- libusb-1.0 >= 1.0.9
- glib-2.0
- gio-unix-2.0

## Compiled Versions

| Version | Status | Date |
|---------|--------|------|
| 0.15.0 | built | 2026-07-19 |

## Build System

- Meson (>= 0.53)

## Upstream

- GitLab: https://gitlab.freedesktop.org/spice/usbredir
- Download: https://spice-space.org/download/usbredir/
