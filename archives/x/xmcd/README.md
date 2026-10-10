# xmcd

xmcd is a Motif/X11 CD audio player and CD database tool from the Unix desktop
era (last upstream release 3.3.2, 2006). It plays audio CDs through the CD-ROM
device, queries/updates CDDB (free and commercial services), keeps a local
discography, and ships a companion CLI controller plus a CDDB browser.

## Package contents

- `bin/xmcd` — Motif GUI player (discography browser, CDDB submit, remote mode)
- `bin/cda` — command-line controller (play/stop/query; also usable from
  scripts and as a remote control client)
- `bin/gobrowser` — CDDB protocol browser helper used by the GUI
- Support data: app-defaults, help pages, man pages and the `xmcd` sample
  configuration installed under the package data prefix
- License: GPL-2.0-or-later (see upstream `docs_d/COPYING`)

## OpenHarmony adaptation

- **Build system**: upstream is a Makefile.std / imake project. OHOS ships no
  `imake`/`xmkmf`, so the recipe uses the bundled `Makefile.std` path
  (`make -f Makefile.std Makefiles` to generate per-directory Makefiles, then
  `make -j1`), with include/library flags expanded from Conan dependencies
  instead of shell environment variables.
- **musl libc gaps** (all handled by feature macros or build flags, never by
  platform macros in patches):
  - no `<termio.h>` → `-DUSE_TERMIOS` (POSIX termios path);
  - `HZ` undefined → `-DHZ=100` (SCSI Generic timeout conversion only);
  - no `pthread_cancel(3)`/`pthread_setcancelstate(3)`, and the sysroot
    `libpthread.a` is an empty shell → `-DHAVE_PTHREAD_CANCEL=0`: self-abort
    call sites go through a feature-macro indirection falling back to
    `pthread_exit()`, cross-thread cancel points degrade to "log + no-op" and
    rely on the existing stop/join teardown path.
- **Dependencies**: `motif/2.3.8`, `libxt/1.3.1`, `libxext/6.4.0.1` and
  `libx11/1.8.13` (forced: libxt/motif pin 1.8.13 while libxext pins 6.4.0 —
  the same combination used by `libXmu/1.3.1`), plus `ncurses/6.6` for `cda`.
- **Headless verification**: the client libraries and CLI paths are exercised
  by `test_package/` against the packaged binaries (`cda -h`, `xmcd -h`) with
  no display server. Interactive GUI behaviour requires a Motif-capable
  desktop session and is out of scope for the L1 test.

## Usage

```bash
# after conan install xmcd/3.3.2 (VirtualRunEnv provides PATH/LD_LIBRARY_PATH)
cda -h                       # CLI controller banner + usage
xmcd                         # starts the Motif player (needs a display)
xmcd -h                      # option summary / initialization diagnostics
```

## Notes on upstream availability

The original upstream site (`tikan.org`) is only reachable over plain HTTP and
no longer serves the release tarball; sources are taken from the FreeBSD
official distfile mirror (`pkg.freebsd.org/ports-distfiles`), whose sha256
matches the port metadata. No test suite exists upstream, so the
HarmonyOS-specific consumer test under `3.3.2/test_package/` is the
verification entry point declared in `3.3.2/reports/test-report.md`.
