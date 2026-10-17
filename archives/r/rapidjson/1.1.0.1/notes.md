# rapidjson 1.1.0 adaptation notes

## Build environment

- Platform: OpenHarmony PC aarch64
- Compiler: clang/clang++ 15.0.4
- CMake: 4.1.2
- Conan: 2.29.1 (OHOS 适配版)
- Build system: CMake
- Package type: header-only (`header-library`)
- Status: built

## W0/W0b and source

- W0: preflight passed; the recipe has one Conan dependency, `gtest/1.17.0`,
  which is published in the ohpcd registry.
- W0b: `archives/r/rapidjson/1.1.0` 已存在一份旧草稿（2026-04-26 创建 /
  2026-07-16 末次改动，status `adapting`、`RAPIDJSON_BUILD_TESTS=OFF`、
  零补丁、手动装头文件方案、真机预检 evidence 失败）——本配方完整替换它：
  版本级 7 个文件改写、`patches/` 与 `unit.cpp`/`ohos_portability.cpp` 新增、
  旧 `test_package/test_package.cpp` 删除、库级 README/manifest 同步改写。
  Reference recipes read: cxxopts 3.2.0 (header-only packaging), jsoncpp
  1.9.8.1 (upstream-test-in-build + OHOS signing pattern), gtest 1.17.0 /
  gmock 1.17.0 (CMakeDeps target names).
- Upstream tag: v1.1.0, commit f54b0e47a08782a6131cc3d60f94d038fa6e0a51.
- Source URL: https://github.com/Tencent/rapidjson/archive/refs/tags/v1.1.0.tar.gz
- Source SHA256: bf7ced29704a1e696fbccf2a2b4ea068e7774fa37f6d7dd4039d0787f8bed98e.

## Upstream test issues and patches

The upstream correctness suite is a single gtest executable (`unittest`)
built from 25 sources under `test/unittest/`. Three problems block building
it as-is on the HarmonyOS toolchain:

1. **gtest source lookup is impossible in release tarballs.**
   `test/CMakeLists.txt` resolves gtest via `FindGTestSrc.cmake`, which
   searches for gtest *sources* (the `thirdparty/gtest` submodule — not
   shipped in GitHub release tarballs — or a Debian-style
   `/usr/src/gtest`). When nothing is found the whole suite silently
   skips. Patch 0002 replaces this with `find_package(gtest CONFIG
   REQUIRED)` against the packaged `gtest/1.17.0` and adds a local
   `gtest_main` shim (`test/gtestmain.cpp`), because the gtest package
   does not ship `gtest_main` as a separate library.
2. **2016-era warning flags fail on modern compilers.**
   Root and unittest CMakeLists add `-Werror` (plus `-Weverything` in the
   unittest Clang branch) to 2016-era sources; modern clang 15 surfaces
   deprecation and other warnings as hard errors. Patches 0001/0003
   drop `-Werror`/`-Weverything` while keeping the informative warning
   flags.
3. **Packaged gtest 1.17 requires C++17.**
   Upstream pins `-std=c++11`, below gtest 1.17's minimum. Patch 0001
   modernizes the test build to `-std=c++17`. (The headers themselves
   remain C++11-compatible; consumers can compile at C++11.)

Additional cleanups in the patches: `export(PACKAGE)` is removed (the
signature was removed from CMake long ago and serves no purpose here);
example installation is guarded by `RAPIDJSON_BUILD_EXAMPLES`;
`valgrind_unittest` and the Debug-only `symbol_check` CTest registrations
are removed (valgrind is unavailable on HarmonyOS; both are re-runs of the
same binary, not additional logical cases); the `perftest` benchmark suite
is not built — it measures throughput, not correctness. No test was
deleted or weakened.

4. **`/tmp` does not exist on HarmonyOS; test temp files move to the
   working directory.** `test/unittest/unittest.h` `TempFile()` uses
   `mkstemp("/tmp/fileXXXXXX")`. On HarmonyOS `/tmp` is not writable, so
   `mkstemp` fails and 6 file-stream tests break — five fail cleanly with
   `fp_ != 0`, one (`OStreamWrapper.ofstream`) segfaults on `fclose(NULL)`.
   Patch 0004 changes the template to a relative `fileXXXXXX`, which
   `mkstemp` creates in the CTest working directory (`bin/`). Same
   behaviour on Linux where `/tmp` is writable.

`CMAKE_POLICY_VERSION_MINIMUM=3.5` is set in the recipe (knowledge E187):
upstream declares `cmake_minimum_required(VERSION 2.8)`, which CMake 4.x
no longer accepts.

## Test inventory

Logical cases are counted once. The authoritative count is the gtest
runtime report of the `unittest` executable:

    ctest --test-dir build --output-on-failure --no-tests=error

`test_package/UPSTREAM-TEST-INVENTORY.md` keeps the static per-source
declaration table (738 lines matching TEST/TEST_F/TEST_P across 25
sources) for review convenience, but 738 is NOT the number of executed
cases: the runtime report is **343 tests from 29 test suites**.

| Category | Cases | Evidence |
|---|---:|---|
| Upstream unit | 343 (gtest runtime) | gtest `unittest` executable, run in `build()` |
| Consumer unit | 1 | `test_package/unit.cpp` |
| HarmonyOS-specific | 1 | `test_package/ohos_portability.cpp` |

OHOS aarch64 (conan create on the device, 2026-09-24): **343/343 passed,
0 failed** — ctest `1/1 Test #1: unittest Passed`, gtest report
`343 tests from 29 test suites ran`.

(For the record: a Windows dry-run of the upstream suite with the same
patches gave 337/343. All 6 failures use `tmpnam()`-generated file
names, which on MinGW resolve to drive-root paths (`\s92c.0`) that
`fopen` cannot open — a Windows runtime artifact, not present on
HarmonyOS.)

Excluded from the count: perftest benchmark suite, valgrind re-run,
Debug-only symbol_check.

## Adaptation

- No library source/API changes were needed; the library is header-only.
- `conanfile.py` uses `package_type=header-library`, installs the upstream
  headers and CMake package config, and runs the upstream CTest suite in
  `build()` (with self-signing of the test executable on OHOS, same
  pattern as the jsoncpp 1.9.8.1 recipe).
- `test_package` is a real C++ consumer that links the CMakeDeps-generated
  `rapidjson::rapidjson` target and exercises DOM parse/mutation/
  serialization/round-trip plus HarmonyOS portability checks.
- This task is Path A. Knowledge E187 (CMake 4.x policy minimum) already
  covers the only cross-repository knowledge applied.

## 真机验证回填（2026-09-24）

`conan create`（OHOS SDK 26.0.0.18 / clang 15.0.4 / aarch64）全绿：

- 上游 gtest 套件 `unittest`：`1/1 Test #1: unittest Passed`（1.08 s），
  gtest 运行时报告 343/343 passed、0 failed
- `test_package`：`2/2` passed —— `rapidjson_unit_consumer` 0.03 s、
  `rapidjson_ohos_portability` 0.02 s
- 包引用：`rapidjson/1.1.0#a5fc1ef9a7655f4f035a151b904b742a:6b129b068851896169fae42d399fa922d239ce8a#d0417f018c576b2eacb19e401980c387`
- 三个测试二进制均通过 `binary-sign-tool sign -selfSign 1` 签名（OHOS 运行前提）
- 日志中的告警均为良性：C++17 下 `std::iterator` 弃用、`RAPIDJSON_ASSERT` 在
  noexcept 函数中的抛异常告警、gtest TYPED_TEST_CASE 弃用提示；`make` jobserver
  mkfifo EPERM 与 `/proc/meminfo` 解析提示为 HMDFS 环境噪音，均不影响构建与运行

---

**编译结束**: 2026-09-24
**最终状态**: built
