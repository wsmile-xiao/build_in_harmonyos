# YubiKey Personalization (ykpers)

> Yubico ykpers: libykpers-1 library + ykpersonalize/ykchalresp/ykinfo CLI tools for configuring YubiKey hardware tokens.

## Introduction

ykpers is Yubico's YubiKey personalization toolkit, providing:

- `libykpers-1`: C library encapsulating YubiKey configuration operations
- `ykpersonalize`: CLI tool to set YubiKey OTP/Challenge-Response slots
- `ykchalresp`: CLI tool to perform Challenge-Response operations
- `ykinfo`: CLI tool to query basic YubiKey information

## OHOS Adaptation Notes

1. **Bundled dependency build**: libyubikey/1.13 and libusb/1.0.27 have no Conan recipes on OHOS; their upstream tarballs are bundled into ykpers conandata.yml and built in-tree to a staging prefix (unpaper/FFmpeg, bowtie2/simde pattern).
2. **config.guess/config.sub reuse**: libyubikey (2013) and libusb (2022) config.guess do not recognize HarmonyOS; ykpers already-patched config.guess/config.sub are copied into both bundled dependency directories.
3. **HMDFS umask fix**: HMDFS `umask 077` causes `mktemp -d` tmp dir permission errors; ykpers and libusb configure both need `umask 077 to 022`.
4. **Duplicate symbol fix**: `ykpers-args.h` `usage`/`optstring` variable definitions cause linker duplicate symbol errors; changed to `extern` declarations.
5. **TRUE/FALSE macros**: HarmonyOS system headers do not define `TRUE`/`FALSE`; added manually in `ykpers-json.c`.
6. **libusb system header conflict**: `linux_netlink.c` `linux/socket.h` vs `sys/socket.h` sockaddr_storage redefinition; guarded with `#define sockaddr_storage __linux_sockaddr_storage`.
7. **libusb kernel version parsing**: `linux_usbfs.c` `get_kernel_version()` cannot parse `HongMeng Kernel X.Y.Z` format; HongMeng keyword detection added, reports Linux 5.10.0.
8. **Static linking**: libyubikey, libusb built `--enable-static --disable-shared`; ykpers links static libs (R26).
9. **make -j1**: avoid HMDFS make jobserver mkfifo permission issues.
10. **Command-line tool package**: software-level directory provides `commands.json` (R38).

## Dependencies

- `json-c/0.18` (Conan dependency)
- `libyubikey/1.13` (bundled source build, no standalone Conan recipe)
- `libusb/1.0.27` (bundled source build, `--disable-udev`)

## Verification

`test_package` runs:

```bash
ykpersonalize -V
ykinfo -V
ykchalresp -V
```

CI environment has no YubiKey hardware; USB errors are expected, only `-V` exit code and output are asserted.
