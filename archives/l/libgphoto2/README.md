# libgphoto2

libgphoto2 is the core library for accessing digital cameras. It provides a framework for camera drivers (camlibs) and I/O drivers (iolibs) to communicate with a wide range of cameras.

## Version 2.5.31

- **Status**: published
- **Build Date**: 2026-06-04
- **Platform**: OpenHarmony (aarch64-unknown-linux-ohos)

### Features
- Core camera access library (libgphoto2.so.6)
- Port/IO library (libgphoto2_port.so.12)
- 17 camera drivers (camlibs) including PTP/IP, Canon, PTP2, etc.
- 2 I/O drivers: disk and ptpip (USB disabled)
- pkg-config support: libgphoto2.pc and libgphoto2_port.pc

### Dependencies
- libltdl/2.4.3a (libtool's dynamic loading library)
- libexif/0.6.26 (EXIF metadata library)
- popt/1.16 (command line option parsing)
- zlib/1.3.1 (compression library)

### Platform Notes
- USB IOLib disabled (--without-libusb1) due to OpenHarmony USB API differences
- NLS disabled (--disable-nls) to avoid gettext complexity
- libltdl built separately from libtool 2.4.3a source before configuring