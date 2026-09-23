# liquidsfz 0.4.1 adaptation notes

## Scope

- Official source: GitHub release asset `liquidsfz-0.4.1.tar.bz2`
  (swesterfeld/liquidsfz, published 2026-04-07, release id 306155210).
- Source SHA-256:
  `b086b371f28fce0d8e882b0b5b9abb71b2124875cf743f4d527bbcb8a4e13f02`
  (verified on the device after mirror download; matches the GitHub asset).
- License: MPL-2.0 (`LICENSE` in the archive root). The bundled 3rdparty code
  (pugixml/imgui/pugl, MIT) only participates in the LV2 GUI path, which is
  disabled on OHOS.

## Dependency gate

The only hard dependency is libsndfile
(`PKG_CHECK_MODULES(SNDFILE, [sndfile])`, unconditional). `libsndfile/1.2.2`
is published on the OHOS PC Conan remote and is declared as the public
requirement: `liquidsfz.pc` embeds `SNDFILE_LIBS`/`SNDFILE_CFLAGS`, so
consumers of the liquidsfz package need libsndfile metadata for static
linking. JACK+readline and LV2+X11 front-ends are optional upstream and are
explicitly disabled (`--without-jack --without-lv2`): the OHOS device has no
jackd runtime and no X11/xrandr/xcursor stack. FFTW (optional, testing only)
stays disabled; `testupsample` therefore is not built and not part of TESTS.

## Build design

The release archive ships generated Autotools files, so the recipe never runs
autoreconf. The single source patch teaches the bundled 2018-era GNU config
scripts (old-style, no `GUESS=` variable, timestamp 2018-02-22/24) the OHOS
triplet:

- `config.guess`: adds `aarch64:HarmonyOS:*:*` ->
  `aarch64-unknown-linux-ohos`, inserted before the `aarch64:Linux:*:*` case.
  Without it configure aborts with "unable to guess system type" on a
  HarmonyOS host (`uname -s` = HarmonyOS).
- `config.sub`: double anchor per DRAFT-E564 — `linux-ohos*` in the
  `maybe_os` kernel split (so `aarch64-unknown-linux-ohos` parses as
  `aarch64-unknown` + `-linux-ohos`) and `-linux-ohos*` in the basic `-os`
  list (so the canonicalized form validates). Both anchors were verified on
  the device: `sh config.guess` prints `aarch64-unknown-linux-ohos` and
  `sh config.sub aarch64-unknown-linux-ohos` accepts it unchanged.

The host OS branch of `configure.ac` then matches `linux*` -> COND_LINUX
(host_os `linux-ohos`), so the Linux code paths and `PLUGIN_EXT=so` are
selected correctly.

The build mirrors the libicns 0.8.1 OHOS pattern: configure, make, check and
install run under the generated Conan build environment with
`SHELL`/`CONFIG_SHELL` overridden to `/system/bin/sh` (avoids the HNP Bash
libtool quote-escaping corruption, E551, and HNP bash getcwd failures inside
HMDFS build folders). Before configure, the recipe requires exactly two
upstream `umask 077` sites and rewrites them to `umask 022` so
`config.status` does not create HMDFS temporaries the effective user cannot
write (fails closed if the upstream layout changes). `TMPDIR` is bound to a
build-local `.tmp` directory and `MKDIR_P` to `/system/bin/mkdir -p`. Every
make invocation is serial. Autotools chain timestamps are pinned to one
identical value after patching so maintainer rules never regenerate the
patched tree through `missing(1)`.

`libsndfile` is discovered by `pkg-config` with `PKG_CONFIG_PATH` pointing at
the PkgConfigDeps-generated `sndfile.pc` in the Conan generators folder. The
`sndfile.pc` baked into the published libsndfile package carries an absolute
prefix from the publishing machine and would resolve `sndfile.h` to a
non-existent directory — the explicit `PKG_CONFIG_PATH` (set before the
toolchain environment snapshot) makes the generated pc win.

Patches are applied in `source()` (not `build()`): Conan keeps the cached
source folder across rebuilds, and a second `patch` run would stop at the
"previously applied" prompt.

## Package shape

Static-only by design: `AC_DISABLE_SHARED` + `LT_INIT([pic-only])`; the
recipe passes `--disable-shared --enable-static` explicitly (shared=True
would work through libtool switches but is discouraged upstream). Installed
artifacts: `lib/libliquidsfz.a`, `include/liquidsfz.hh`,
`lib/pkgconfig/liquidsfz.pc`. The obsolete non-relocatable `libliquidsfz.la`
is deleted; `liquidsfz.pc` is rewritten to `prefix=${pcfiledir}/../..` and
the machine-specific absolute `-L/-I` SNDFILE paths (baked from the build
conan cache) are stripped, keeping the logical `-lsndfile` link requirement.
libtool version-info 4:1:0 (from 0.4.1) is preserved by upstream design.

## Tests

Upstream `tests/Makefile.am` runs `TESTS = testsynth testsfzreader` under the
automake test harness (`test-driver`):

- `testsynth` generates `testsynth.wav` with libsndfile, writes
  `testsynth.sfz`, renders and does sine-detection assertions (offline).
- `testsfzreader` parses SFZ content in memory (offline).

Both run in the tests build directory (writable) and need no audio device,
X11, network or external fixtures. On the device both PASS unsigned — no
binary signing is required for locally built test executables on this
HarmonyOS PC target (verified: `make check` -> `# PASS: 2 / # TOTAL: 2`).

The Conan consumer test (`test_package/test_liquidsfz.cc`) renders a real
note through the installed static library: it writes a minimal PCM16 WAV
fixture directly (no sndfile.h include — see the known gap below), references
it from a generated SFZ file, loads it with `LiquidSFZ::Synth`, plays MIDI
note 60 and asserts a non-silent, bounded output signal. libsndfile is still
exercised on the link path: `libliquidsfz.a` references sndfile symbols and
the consumer target chain pulls `libsndfile.a` in.

Known gap of the published libsndfile/1.2.2 binary (not fixable inside this
package): its `cpp_info.includedirs` materializes empty for consumers, so a
test_package consumer cannot `#include <sndfile.h>` through the CMakeDeps
target (PkgConfigDeps-generated `sndfile.pc` is unaffected and is what the
liquidsfz build itself uses).
Tests are counted by independent entry point: upstream 2/2 + consumer 1/1.
