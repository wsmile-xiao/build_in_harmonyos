# WMRack (wmrack)

> Window Maker / AfterStep dock applet ("Wharf swallowable") that controls the CD-ROM drive and the OSS mixer.

## Introduction

WMRack is a Dock/Wharf applet written by Oliver Graf, maintained since 2003 by Chris Waters
(`xtifr@users.sourceforge.net`). It gives complete control over the CD-ROM drive and the mixer:

- **CD functions**: track and time display (remaining / to-go, track / total), play, pause, stop,
  eject, load, track +/-, fast forward/backward, random play, data-track skipping, play lists.
- **Mixer functions**: startup volume, all mixer devices, balance, record source selection.
- Highly configurable look: the XPM style compiled into the binary is chosen with a symbolic link
  (`XPM/standart.style -> <style>.style`) at build time.

The package produces a single `wmrack` executable (C, X11 dockapp) linking `-lXpm -lX11 -lXext`.

Upstream: <https://sourceforge.net/projects/wmrack/> (release 1.4, 2007-11-26), GPL-2.0-or-later.

## OHOS Adaptation Notes

1. **X11 detection (`AC_PATH_X`)** — the upstream `configure` probes `X11/Xlib.h` in the traditional
   `/usr/X11R6` style locations. On OHOS the X11 headers and libraries come from Conan packages, so
   the recipe always passes `--x-includes=<libx11 include dir>` and `--x-libraries=<libx11 lib dir>`.
   Without them `configure` stops with `WMRack needs X Windows!!!`.
2. **Link line / `-L` search paths** — `configure.in` puts the X11 library directory into `LIBS` and
   `AC_CHECK_LIB` appends `-lXpm` / `-lXext`, but the matching `-L` directories of the Xpm/Xext
   packages have to come from the command line (`LIBS=...`). The recipe derives them from the
   dependency graph, so `ld.lld` finds every X library.
3. **Cross compilation** — `configure` is invoked as `./configure --host=aarch64-linux-ohos ...`.
   `AC_CHECK_LIB` only compiles and links its conftest, so nothing has to be executed; the explicit
   `--host` additionally makes a worker that *cannot* execute an aarch64 conftest fall back to
   `cross_compiling=yes` instead of failing hard.
4. **64-bit correctness** — `wmrack.c` uses `time()` while only including `<sys/time.h>`; on arm64
   the implicit declaration of `time()` returns `int`, truncating the 64-bit `time_t`
   (patch `0001-wmrack.c.patch`).
5. **Undefined behaviour in `sprintf`/`sscanf`** — a whole `TrackInfo` struct was passed to a `%02d`
   conversion (now `.num`) and `char (*)[1024]` instead of `char *` was passed to `%s`
   (patch `0001-wmrack.c.patch`); `fprintf(stderr, buffer)` used a non-literal format string
   (patch `0002-xpmicon.c.patch`). After the patches the OHOS clang 15 build is warning-free.
6. **E114 — Autoconf scratch directories** — the Autoconf 2.61 generated `configure` creates its
   temporary directories with `umask 077 && mktemp -d "./confXXXXXX"`. On HMDFS such a directory can
   end up unwritable even for its owner. `build()` rewrites both occurrences to `umask 022` before
   running `configure`.
7. **E002 / E074** — `/tmp` is a read-only erofs mount (`TMPDIR` is redirected into the Conan build
   folder) and `make` must run with `-j1` because SELinux denies the FIFO jobserver.
8. **Runtime smoke test** — OHOS has no X server, so the consumer test asserts that the installed
   binary resolves its Xpm/X11/Xext dependency chain and reaches `XOpenDisplay` (expected:
   `can't open display`), and that the compiled-in style library is installed next to the binary.

## Dependencies

- libxpm/3.5.17
- libx11/6.4.0
- libxext/6.4.0.1

## References

- <https://sourceforge.net/projects/wmrack/>
- GPL-2.0-or-later
