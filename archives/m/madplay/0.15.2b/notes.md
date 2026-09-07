# madplay 0.15.2b adaptation notes

## Upstream

- Project: MAD — MPEG Audio Decoder, by Robert Leslie; hosted at
  https://sourceforge.net/projects/mad/ (files/madplay/0.15.2b).
- `madplay-0.15.2b.tar.gz` (590929 bytes) SHA256:
  `5a79c7516ff7560dffc6a14399a389432bc619c905b13d3b73da22fa65acede0`
  (cross-verified: SourceForge download and the Debian
  `madplay_0.15.2b.orig.tar.gz` pool copy are byte-identical).
- License: GPL-2.0-or-later (source headers; the tarball's COPYING is the
  GPLv2 text). This is a CLI application package, license compliance is at
  the consumer's responsibility.
- 0.15.2b (2004-02-25) is the final official madplay release.

## Dependencies (from configure.ac, verified against source)

- `libmad` (mad.h + AC_CHECK_LIB(mad, mad_decoder_init)) — hard requirement;
  satisfied by the repository package `mad/0.16.4`.
- `libid3tag` (id3tag.h + AC_CHECK_LIB(id3tag, id3_file_open, [-lz])) — hard
  requirement; satisfied by `libid3tag/0.16.3`. Note: SourceForge hosts
  libid3tag only up to 0.15.1b; 0.16.3 is the Debian-maintained upstream
  tarball that the repository's libid3tag/0.16.3 recipe uses.
- `zlib` — id3tag is linked with -lz at configure time; satisfied by the
  repository package `zlib/1.3.1`.
- Everything else ( curses, audio subsystems: alsa/esd/oss/sun/qtx/…) is
  optional and auto-probed. On OHOS the OSS probe can even succeed if
  <soundcard.h> exists in the sysroot; audio=… only selects the default
  device module. All file-based output modules (wave/raw/snd/aiff/cdda/
  hex/null) compile unconditionally, so no audio device is needed for
  decode-to-file operation.

## Upstream test suite

There is none: madplay is an application. The 0.15.2b tarball has no
`test/` directory, no TESTS/check_PROGRAMS in any Makefile.am, no `check`
or `test` target in the generated Makefile.in, and no CI of any kind. The
only shipped non-build script is `abxtest` (a bash helper for ABX listening
tests, installed as a bin_SCRIPTS). Upstream verification is therefore
impossible; the Conan test_package provides the on-device verification.

## Patches

- `0001-config.sub-aarch64.patch` (portability): the bundled 2001-era
  `config.sub` does not know aarch64; the patch adds the
  `aarch64-unknown-linux-ohos` triplet acceptance. Nothing else is changed.
- `0002-configure-umask-022.patch` (portability, 1 line): configure's
  confstat tmp dir is created with `umask 077`; on this OHOS toolchain's
  filesystem that makes the dir unreadable for the compile checks. Use
  umask 022 (same knowledge point as mpg123's notes).
- Everything else compiles unmodified — madplay 0.15.2b builds cleanly
  with OHOS clang 15 and musl (verified by a native on-device build).

## Build notes

- Autotools; built with `--build=aarch64-unknown-linux-gnu
  --host=aarch64-unknown-linux-ohos` (cross triplet passed explicitly
  because `uname -s` is "HarmonyOS", which config.guess does not know).
- `make -j1`: 2004-era libtool/demo Makefile fragments do not cope with
  parallel makes under this toolchain.
- `make install` installs bin_PROGRAMS (madplay) and bin_SCRIPTS (abxtest);
  libtool `.la` files are removed from the package.

## test_package design

- `gen_fixture.c` writes a deterministic silent MPEG-1 Layer III stream
  (128 kbps mono 44100 Hz, 417-byte frames, all-zero side info and
  payload). No binary fixture from unknown provenance is used.
- madplay is invoked for real, on-device:
  - `--version` — asserts all three banners (mad, libid3tag, "madplay
    0.15.2" — the banner prints "0.15.2 (beta)", the tarball is 0.15.2b).
  - `--help` — usage line.
  - `-T fixture.mp3` — tags-only parse path (decode_filter returns
    MAD_FLOW_STOP after the first tag scan; no audio module involved).
  - `-o wave:out.wav fixture.mp3` — full decode: canonical 44-byte RIFF/
    WAVE header (PCM16 mono 44100), then 25*1152 samples. libmad's default
    dither keeps a silent stream within |x| <= 2 (peak about -80 dB), so
    the assertion checks the sample range rather than exact zeros.
  - `-o hex:out.hex fixture.mp3` — full decode to text: header line
    "# 1 channel, 44100 Hz, 24-bit samples" then 25*1152 hex samples.
  - negative: `-T nonexistent.mp3` must exit non-zero (exit 4, open
    failure).
  - negative: garbage bytes decode zero frames; the wave module still
    writes its 44-byte header on init, so the output is exactly 44 bytes
    with no PCM payload.
