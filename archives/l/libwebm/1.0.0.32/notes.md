# libwebm 1.0.0.32 HarmonyOS PC notes

## Source

- Upstream: https://github.com/webmproject/libwebm
- Tag: `libwebm-1.0.0.32` (note the `libwebm-` prefix; the unprefixed
  `1.0.0.32` tag URL is a 404)
- SHA256 of the tag tarball:
  `7fd5e085bda9f8031cf2ad2a1e52d9b7b29cba9c0b96ad2ce794ce89e4249eb8`
- License: BSD-3-Clause (LICENSE file in the repo root)

## Build design

- The packaged library target is `webm` — an aggregate of the
  `libwebm_common`, `mkvmuxer`, `mkvparser` (and with
  `ENABLE_WEBM_PARSER=ON`, the new `webm_parser` API) object libraries.
  Public headers install under `include/webm/{common,mkvmuxer,mkvparser}`,
  plus `include/webm/*.h` for the new parser API.
- Upstream CMake options and the values used:

  | Option | Upstream default | Recipe value |
  |---|---|---|
  | `ENABLE_WEBMTS` | ON | OFF |
  | `ENABLE_WEBMINFO` | ON | OFF |
  | `ENABLE_SAMPLE_PROGRAMS` | ON | OFF |
  | `ENABLE_WEBM_PARSER` | OFF | ON (recipe option `enable_webm_parser`) |
  | `ENABLE_TESTS` | OFF | OFF in the package build, ON in the test tree |

  `ENABLE_WEBMTS`/`ENABLE_WEBMINFO`/`ENABLE_SAMPLE_PROGRAMS` only build
  extra executables, never library code, so disabling them keeps the
  package a pure `libwebm.so`/`libwebm.a`.
- No third-party runtime dependencies; the shared library NEEDED set is
  exactly `libc++_shared.so` and `libc.so` (musl).

## SONAME handling (E330/E383)

Upstream `add_library(webm ...)` sets no SOVERSION, so on Linux the .so
would ship without a DT_SONAME. On OHOS the situation is worse: CMake 4.x
ships no `Platform/HarmonyOS.cmake`, which leaves
`CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` empty and the .so unversioned with
no SONAME at all. The recipe fixes this in `generate()`:

- `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` / `..._CXX_FLAG` = `-Wl,-soname,`
- `CMAKE_PLATFORM_NO_VERSIONED_SONAME` = TRUE (no versioned symlink churn)

The result is `DT_SONAME=libwebm.so`, verified in the consumer test with
readelf. This follows the E383 recommendation (toolchain flags, not a
patch — nothing in the upstream tree needs to change).

## Upstream tests (R51)

libwebm registers nothing with CTest; each suite is a standalone gtest
binary. The recipe builds them in a second, static configure/build tree
(`build/Release/upstream-tests`) with `ENABLE_TESTS=ON` and executes each
binary directly. Two environment details matter:

- `GTEST_SRC_DIR` must point at the googletest repo root (upstream does
  `add_subdirectory(${GTEST_SRC_DIR})` and references
  `googletest/include` and `googlemock/include` beneath it). googletest is
  not a submodule in the release tarball, so the recipe pins the commit
  documented in `README.libwebm` — `ddb8012` (2015-12-10) — as a source in
  conandata.yml and unpacks it into `third_party/googletest`.
- googletest ddb8012 declares `cmake_minimum_required(2.8)`, which CMake
  4 rejects; the test tree is configured with
  `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` (same override as leveldb's).
- Test data: suites resolve `.webm` fixtures via the
  `LIBWEBM_TEST_DATA_PATH` environment variable (testing/test_util.cc), not
  the CWD. The recipe exports it pointing at `testing/testdata` in the
  source folder. `mkvmuxer_tests` also writes temp files via `TEST_TMPDIR`
  (common/file_util.cc), which the recipe points at a writable directory
  inside the build tree.

Result on the HarmonyOS PC (armv8 native, `-pr:h -pr:b ohos-aarch64`):
all 6 suites pass — mkvmuxer_tests 32, mkvparser_tests 27,
webm_parser_tests 307, vp9_header_parser_tests 4, vp9_level_stats_tests 3,
webm2pes_tests 7 (380 total, 0 failures). No test input, assertion, or pass
condition was modified.

Note: `conan create` with only `-pr` (host profile) leaves the default
Linux x86_64 build profile active, `can_run()` becomes false, and the
recipes degrades to compile-only. Always pass both profiles on the PC
(`-pr:h ... -pr:b ...`); this matches the leveldb notes.

## Consumer test

`test_package/test.cpp` performs (34 assertions):

1. Mux a WebM file programmatically with `mkvmuxer` (VP8 track, 320x240,
   3 frames, 2 clusters) — no checked-in binary fixture.
2. Parse it back with `mkvparser`: doc type, track count/type/codec,
   cluster timecode, 3 blocks.
3. Parse the same file with the new `webm_parser` API (`FileReader` +
   `WebMParser::Feed` + callback counting track entries, clusters,
   simple blocks, timecodes).
4. Error inputs: empty stream completes as an empty document (documented
   Feed() semantics — a parser that crashes or misreports here fails);
   garbage input is reported as a parsing error (`is_parsing_error()`);
   truncated EBML header does not complete; `mkvparser` rejects an empty
   file at the EBML header.
5. OHOS gates (test_package/conanfile.py): readelf verifies ELF64 +
   AArch64, `DT_SONAME=libwebm.so`, and a clean NEEDED set; the consumer
   binary is signed with `binary-sign-tool` (`.codesign` section) before
   execution, following the lapack precedent.

## Known quirks

- Upstream headers include each other as `"mkvmuxer/..."` /
  `"common/..."`, i.e. relative to `include/webm`, not the package root.
  Consumers using `<webm/mkvmuxer/mkvmuxer.h>` must also add
  `$LIBWEBM_ROOT/include/webm` to their include path (the test package
   demonstrates this), or include as `<mkvmuxer/mkvmuxer.h>` with the
   package include dir. This is upstream's chosen layout, unchanged here.
- `mkvmuxer::Segment::AddVideoTrack(width, height, number)` returns the
  allocated track number; `number=0` means "auto".
- The upstream `AddFrame(..., timestamp_ns, is_key)` takes nanosecond
  timestamps; the consumer test passes frame indices only because the
  assertions never check absolute time.
