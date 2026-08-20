# libsndfile 1.2.2 upstream test inventory

Date: 2026-08-17

The pristine source SHA256 matched `conandata.yml`. Its top-level
`CMakeLists.txt` contains 143 textual `add_test(...)` declarations under
`BUILD_TESTING`, including optional-codec and platform-specific conditions.

The HarmonyOS package keeps `BUILD_TESTING=ON` for the default static build and
runs these 12 deterministic core entries with CTest:

- `test_main`
- `sfversion`
- `error_test`
- `ulaw_test`
- `alaw_test`
- `command_test`
- `checksum_test`
- `headerless_test`
- `rdwr_test`
- `format_check_test`
- `channel_test`
- `virtual_io_test`

This subset covers internal conversions/codecs, errors, command handling,
headers, read/write behavior, format validation, channel handling, virtual I/O,
and version reporting. The optional FLAC/Vorbis/Opus/MPEG tests are unavailable
because their unpublished dependencies are intentionally disabled. The broad
format matrix plus pipe/stdio cases are trimmed from the mandatory device gate
to keep a single-package run bounded and filesystem-independent.

The installed-package test separately performs a real WAV/PCM file round trip
through the exported `SndFile::sndfile` target.
