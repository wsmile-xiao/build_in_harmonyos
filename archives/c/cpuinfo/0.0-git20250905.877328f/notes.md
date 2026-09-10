# cpuinfo 0.0-git20250905.877328f notes

Upstream: pytorch/cpuinfo @ 877328f188a3c7d1fa855871a278eb48d530c4c0.
Snapshot version 0.0-git20250905.877328f. CMake library, zero runtime deps.

## OHOS adaptation
- Upstream CMakeLists supports Windows/Darwin/Linux/Android/FreeBSD/Emscripten
  only; on OHOS `CPUINFO_SUPPORTED_PLATFORM` would be FALSE and no tests built.
  Patch `0001-ohos-support.patch` remaps `CMAKE_SYSTEM_NAME STREQUAL OHOS`
  to Linux right after `PROJECT()` (HongMeng Kernel provides /proc/cpuinfo,
  sysfs, pthreads, ARM Linux sources), so Linux/ARM sources, unit tests,
  tools and Threads all apply.
- GTest vendored in `source()` from conandata `googletest` entry
  (v1.14.0, cmake_minimum 3.13, required for device CMake 4.4.3)
  into `deps/googletest` with
  `GOOGLETEST_SOURCE_DIR` set; avoids configure-time download via
  `cmake/DownloadGoogleTest.cmake`. Benchmarks OFF, mock tests OFF
  (zero mock cases on Linux anyway).
- Tools ON (isa-info/cpu-info/cache-info installed with the library).

## Tests
- Upstream audit: `test/init.cc` 133 TEST, `test/get-current.cc` 4 TEST =
  137 gtest cases in 2 ctest binaries (init-test, get-current-test).
  `build()` runs `ctest --output-on-failure`, parses `[PASSED]/[FAILED]/
  [SKIPPED]` verdicts, requires executed==137 with zero fail/skip,
  emits `HMBS_UPSTREAM_TEST_RESULT` (print + info) and persists
  `hmbs_upstream_result.json` into the package for cache-hit re-emission.
- test_package: `test_cpuinfo.c` consumer (init + topology, 2 cases);
  `test()` re-emits upstream marker then runs `./test_cpuinfo` and emits
  `HMBS_TEST_PACKAGE_RESULT` (discovered=2/passedCount=2).

## Verification
- Pending HMBS device preflight (conan create + test_package + ctest).
- Falsification: harness requires non-empty ctest output and exact 137
  parsed verdicts; exit 0 alone is not accepted.

## Strategy log (2nd policy cycle)
- Rounds 1-2 backported upstream-main MIDR decodes missing in the snapshot
  (A78C/A520/A720/X4/X925/A725/A320/Lumex-C1/Oryon-v3/Apple); verified exact
  against upstream main src/arm/uarch.c + include/cpuinfo.h, kept.
- Round 3 invented Huawei Taishan-V120 mappings (parts 0xD02/0xD03/0xD06/0xD42
  + taishan_v120 enum) from public articles. Issue: upstream main has NO such
  mappings ('H' still only 0xD01/0xD40, single taishan_v110 enum), so the guess
  had no upstream basis and the single CORE.known_uarch failure persisted.
  Per the no-repeat rule this round REMOVES the fabricated Huawei block/enum
  instead of extending it, and switches to measurement-first: on failure the
  recipe now emits one truncation-proof `HMBS_CPUID raw=[...]` line (raw
  implementer/part/variant combos from /proc/cpuinfo) plus
  `HMBS_UNKNOWN_PART parts=[...]` (exact hex cpuinfo refused to decode).
  The next mapping, if any, will cover only the device-measured part.
- This round got that measurement: HMBS_CPUID raw=[impl=0x48 part=0xd03 x8;
  part=0xd42 x4; part=0xd43 x8] (20 SMT threads = Kirin X90 4+4+2; the earlier
  article-guess had wrongly included 0xD02 and mapped 0xD03 to V110). All
  three measured parts are Taishan V120 generation, so they map to the
  (re-added, upstream-style) taishan_v120 enum; unmeasured parts stay unknown
  by design.
