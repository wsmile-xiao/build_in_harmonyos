# jnoisemeter

`jnoisemeter` is a realtime noise / spectrum level meter for X11: it draws a
peak + RMS meter and a 1/1-octave, parametric-EQ and ITU-R BS.468 style filter
view for a live audio signal. It is written by Fons Adriaensen (C++ / Qt-free
X11 via his own `clxclient` and `clthreads` libraries) and takes its audio
input from JACK.

Upstream: https://kokkinizita.linuxaudio.org/linuxaudio/ (GPL-2.0-or-later)

## Build system upstream

`source/Makefile` only — 52 lines, no `configure`, no CMake, no meson. It
defines exactly four targets (`jnoisemeter`, `install`, `uninstall`, `clean`,
at lines 35 / 41 / 46 / 50) and carries no test target of any kind, so the
upstream test denominator is **0**:

```
$ cd source && make check
make: *** No rule to make target 'check'.  Stop.
```

## OpenHarmony adaptation

Source: https://kokkinizita.linuxaudio.org/linuxaudio/downloads/jnoisemeter-0.4.1.tar.bz2
(sha256 `e20c39b18c378c51e2ac951c0f2fd9fdf2e0137a852246c8a18e3975eb71effe`).
Build system: plain Makefile driven from the Conan recipe; compiler, target
triple and optimisation flags come from the OHOS profile (R33).

One portability patch, `patches/0001-source-Makefile.patch` (+4/-4):

* `CPPFLAGS += $(shell pkgconf --cflags freetype2)` becomes
  `CPPFLAGS += $(PCONFCFL)`. Upstream has no appendable include-path slot, and
  assigning `CPPFLAGS` on the `make` command line replaces it wholesale — the
  upstream `CPPFLAGS += -MMD -MP -DVERSION=\"$(VERSION)\"` (line 25) then
  disappears, which breaks the build because `VERSION` is really used
  (`jnoisemeter.cc:50`, `mainwin.cc:55`). `PCONFCFL` is deliberately a variable
  that is *referenced but never assigned*, so the recipe can inject the Conan
  dependency include dirs through it without touching upstream's own flags.
  Measured with `make -n` and recorded in
  `knowledge/drafts/DRAFT-jnoisemeter-0.4.1-makefile-invented-append-slot.md`.
* `CXXFLAGS += -march=native` removed (clang 15 rejects it on AArch64, and a
  build-host-tuned binary must not ship).
* Both `install` lines in the `install` target go through `$(INSTALL)`, with
  `INSTALL ?= /bin/install`: OHOS userland has no coreutils `install`.

Dependencies resolved by Conan rather than the host: clxclient/3.9.2,
clthreads/2.4.0, libxft/2.3.8, libx11/1.8.13, xorgproto/2025.1 and jack/1.9.22
(transitive: freetype/2.14.3, fontconfig/2.18.3, libxrender/0.9.12,
libxcb/1.17.0, libxau/1.0.11, libxdmcp/1.1.5, libxml2/2.15.3).

## Testing on OpenHarmony

Upstream ships no tests (denominator 0, nothing disabled to shrink it). The
package's own `test_package/` runs 2 cases / 3 assertions for real; jnoisemeter
is an X11 GUI app and a JACK client, so with no display server and no `jackd`
in CI the pass criterion is "loads its full shared-library closure and reaches
an upstream early-exit path": `--help` prints the `jnoisemeter-0.4.1` banner
and returns 1, and running with `DISPLAY`/`XAUTHORITY` unset prints
`Can't open display.` and returns 1 — not 127, which is the loader evidence.

W3 local CI simulation (2026-09-26) verdict, copied verbatim into
`0.4.1/notes.md`: `L0_RESULT=pass`, `L1_RESULT=pass: test_package executed`,
`L2_RESULT=skip: jnoisemeter version/help failed` (recorded as skip, not as a
pass), `L4_RESULT=pass`, `L5_RESULT=pass`, build summary `Success: 1 / Failed: 0`.
