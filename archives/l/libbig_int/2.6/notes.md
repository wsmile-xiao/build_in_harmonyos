# libbig_int 2.6 OpenHarmony adaptation

## Source

Official repository: https://github.com/mlafeldt/libbig_int (a C port of
Alexander Valyalkin's big_int PHP library). The upstream repo has **no 2.6
release tag** — the newest tag is `big_int-1.0.7` (2012); the last master
commit is `fd8f3278` (2020-04-30, "Sync with upstream valyala/big_int").
Task-designated version 2.6; the source is pinned to the official master
HEAD commit's GitHub archive and SHA-256 verified by direct download:
`d13babcc1af8681a15c7e8609a6f72334bdb32b927cbecc85a68b98c7ee993fd`.

## Adaptation

- Upstream build is plain CMake: `PROJECT("libbig_int" C)` +
  `ADD_LIBRARY(big_int ...)` + `INSTALL(TARGETS big_int DESTINATION lib)`.
- Patch `0001-cmake-ohos-adapt.patch` (single patch, three fixes):
  1. `CMAKE_MINIMUM_REQUIRED(VERSION 2.6)` → `3.15`: CMake 4.x refuses
     projects with a minimum version < 3.5.
  2. `SET(CMAKE_C_FLAGS "-Wall -Werror -O2")` → `"-Wall -O2"`: the upstream
     assignment overwrites the whole toolchain flag set (including the OHOS
     `-target`/sysroot flags injected by the Conan toolchain), and `-Werror`
     is a hard-fail risk on 2012-era C code under clang 15.
  3. Added `INSTALL(DIRECTORY include/ DESTINATION include)`: upstream never
     installs headers, so a Conan package would ship a library with no
     public headers; consumers need `include/big_int.h` etc.
- No dependencies (pure C, no requires) — R36 trivially satisfied.
- Static library (`BUILD_SHARED_LIBS` off via default `shared=False`), no
  system-name clash (R26 not triggered).

## Verification

- Clean build from the official tarball + patch: `cmake` exit 0,
  `make -j1` exit 0, `make install DESTDIR` exit 0; artifacts =
  `lib/libbig_int.a` + 12 public headers under `include/`.
- Upstream tests: **none** — full enumeration of the 35-file official tree
  found no test/bench/sample/example/fixture files, no `main()` in any
  source, and no `enable_testing`/`add_test` in CMakeLists (ledger in the
  task report). Dual-caliber stats: `source_declared_total=0`,
  `configured_executable_total=0`, `executed_passed_total=0`.
- Consumer/HarmonyOS test `test_package/test.c` (compiled against the
  installed public headers + static lib only): 10 assertions covering
  `from_int/to_int`, `add` (12345+6789=19134), `mul`
  (12345*6789=83810205), `div` (83810205/12345=6789), decimal string
  round-trip (`to_str`/`from_str`, "987654321"), `gcd(1071,462)=21` — all
  PASS, exit 0, run natively on OHOS aarch64.
- Note: `big_int_add`/`big_int_mul` do not normalize the result length;
  consumers must call `big_int_clear_zeros` before `big_int_to_int`.

## Notes

- Library name in the package is `big_int` (`cpp_info.libs = ["big_int"]`,
  `libbig_int.a`).
---

**编译结束**: 2026-09-26 02:32
**最终状态**: built
