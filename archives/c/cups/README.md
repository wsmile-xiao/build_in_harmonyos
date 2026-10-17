# CUPS

CUPS is OpenPrinting's implementation of the Internet Printing Protocol and a
printing system for Unix-like platforms.

## Features

- IPP and HTTP client/server libraries
- Printer discovery and scheduler tools
- PPD parsing and legacy printer-description support
- Command-line administration and protocol testing tools

## OpenHarmony PC adaptation

The OHOS build uses the native `aarch64-unknown-linux-ohos` target, avoids
libc APIs that are declared but not implemented by the platform, and replaces
HMDFS-incompatible symbolic links with checked regular-file copies. Optional
desktop and system integrations that are unavailable on the build worker are
disabled explicitly in the Conan recipe. OHOS builds are static to isolate
the package from OpenHarmony's distinct `libcups.z.so` system provider. The
scheduler recognizes explicit shell-script filters when HMDFS denies direct
execution and launches only those scripts through the system shell.

## Dependencies

- OpenSSL 3.5.6
- zlib 1.3.1.1
- GNU libiconv 1.17

## References

- https://openprinting.github.io/cups/
- https://github.com/OpenPrinting/cups
