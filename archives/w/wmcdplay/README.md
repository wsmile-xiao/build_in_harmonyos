# wmcdplay

> Window Maker dockapp CD player (an ascd derivative) that drives the CD-ROM device over X11.

## Introduction

wmcdplay is a Window Maker dockapp CD player written in C++:

- Single X11 client executable (`wmcdplay.cc`), artwork compiled in through `#include "XPM/standard.art"`
- Four selectable artwork styles shipped as data (`bluered` / `grey` / `newstyle` / `wmcd` `.art`)
- CD control through Linux `<linux/cdrom.h>` ioctls (`cdctl.h`, with a FreeBSD variant `cdctl_freebsd.h`)
- Links `-lXpm -lXext -lX11` (plus the libxcb family pulled in by libX11)

Upstream: https://www.dockapps.net/download/wmcdplay-1.1.tar.gz, GPL-2.0-or-later.

## OHOS Adaptation Notes

1. **No generated autotools files upstream**: the tarball ships only `configure.ac` / `Makefile.am`. The recipe bootstraps with `aclocal → autoconf → automake` (`autoreconf` is deliberately avoided — its m4 cache chain hits the `autoconf.m4f` conflict on OHOS). The OHOS image has no automake, so `tool_requires("automake/1.18")` supplies it, addressed through `$ACLOCAL` / `$AUTOMAKE` as exported by the package's buildenv.
2. **`AM_CFLAGS` does not cover C++**: `wmcdplay.cc` is C++, so the pkg-config include flags never reached the compile. Patch 0001 adds `AM_CXXFLAGS` with the same `$(x11_CFLAGS) $(xpm_CFLAGS) $(xext_CFLAGS)`.
3. **Non-relocatable `x11.pc`**: `libx11/6.4.0` installs `x11.pc` with `prefix=/`, so include/lib paths must come from `cpp_info` via `AutotoolsDeps`, not from pkg-config alone.
4. **C++11 user-defined literal**: `"Release "VERSION` lexes as a UDL and clang rejects it; patch 0002 inserts the missing spaces around `VERSION`.
5. **Missing path separator**: `-f artwork_file` resolution used `sprintf("%s%s", SYSARTDIR, artfilen)` against a `pkgdatadir` without a trailing slash; patch 0003 inserts `/`.
6. **Cross compilation**: `--host=aarch64-linux-ohos` puts configure into cross mode, so the compiler works-check only links and never tries to run an aarch64 conftest on the build host.
7. **In-source build required**: the `XPM/%.art` rules use `cd XPM && ./makeart $*` relative paths, so out-of-source builds cannot work unpatched.
8. **OHOS packaging**: `patchelf --remove-rpath` → `llvm-objcopy --remove-section .codesign` → `binary-sign-tool sign -selfSign 1`; E490 execute-bit restoration runs on the known autotools helpers and `XPM/makeart` after bootstrap.
9. **Headless consumer check**: `--help` is handled by `scanArgs()` before `initXWin()` and exits 0, so the consumer test needs neither an X server nor a CD device; without `DISPLAY` the binary reports `Unable to open X display` as expected.

## Dependencies

- libx11/6.4.0 (force)
- libxext/6.4.0
- libxpm/3.5.17
- automake/1.18 (tool_requires, build only)

## Upstream Tests

The upstream 1.1 tarball contains **no automated tests** (37 files, no `tests/` directory, no `TESTS` / `check_PROGRAMS` in `Makefile.am`, no ctest/pytest registration). `make check` resolves to the empty automake `check-am` target. The consumer `test_package` therefore carries the verification load: 27 assertions including the HarmonyOS aarch64 consumer run (`harmonyos_aarch64_consumer_run`).
