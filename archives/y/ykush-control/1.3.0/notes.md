# ykush-control 1.3.0 adaptation notes

## Source

- Upstream: https://github.com/Yepkit/ykush
- Release archive: https://github.com/Yepkit/ykush/archive/refs/tags/v1.3.0.tar.gz
- SHA256: 2bb3b2726b446d4d19b2860ca0681afe0956f0d6dc07897ded699665f66ca401

## Build

- Builds the Linux/OHOS command-line tool `ykushcmd`.
- The upstream Linux implementation uses libusb-1.0.
- For OHOS armv8/aarch64, the recipe downloads the official cmd-pkgs
  `libusb-1.0.27-ohos-aarch64.tar.gz`, verifies SHA256
  `52cc022e2a7e1be81f993689c8f326aaca8b97f51e232995d5cc366b860271a3`,
  and links `libusb-1.0.a` statically.
- For OHOS x86_64 emulator validation, the recipe builds libusb 1.0.27 from
  the upstream source archive and links the generated static library for the
  emulator binary.
- The upstream v1.3.0 tag still prints `YKUSHCMD Version 1.2.5`; the recipe
  patches the help string to `YKUSHCMD Version 1.3.0` during build so the
  packaged command reports the adapted release version.

## Upstream tests

- Upstream provides one manual test source: `src/tests/test_usbhid.cpp`.
- Upstream `Makefile_tests` omits the bundled `libusb/` include directory; the recipe compiles the same test source with the required include path.
- The test enumerates YKUSH USB HID devices and exits successfully when no board is attached.

## Added test_package

- Checks packaged `ykushcmd` help output reports version 1.3.0.
- Checks YKUSH-specific `-h` help output.
- Checks offline board listing when no board is attached.
- Checks invalid command handling returns non-zero and prints usage.
