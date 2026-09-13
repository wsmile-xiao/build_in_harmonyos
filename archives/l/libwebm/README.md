# libwebm

libwebm is the WebM project's Matroska/WebM container muxer and parser
library (mkvmuxer, mkvparser, and the newer webm_parser callback API).

## HarmonyOS PC adaptation

- Builds the official `webm` shared library with CMake; sample programs and
  tools are disabled so the package contains only library and headers.
- No third-party Conan dependencies; the shared library links only against
  `libc++_shared.so` and `libc.so` (musl).
- Provides `DT_SONAME=libwebm.so` via toolchain flags because upstream sets
  no SOVERSION and CMake 4 has no HarmonyOS platform module (E330/E383).
- Compiles and runs all 6 googletest-based upstream suites in a separate
  static tree, with the upstream-documented googletest pin (`ddb8012`).

## Verification

The Conan consumer muxes a WebM file programmatically, round-trips it
through both mkvparser and the new webm_parser API, and checks error
inputs (empty/garbage/truncated streams). The package test additionally
verifies AArch64 ELF class/machine, `DT_SONAME`, the NEEDED set, and runs
the signed binary on a HarmonyOS PC. All 380 upstream tests (6 suites) and
the 34 consumer assertions passed on-device.

## Reference

- https://github.com/webmproject/libwebm
- https://www.webmproject.org/code/
