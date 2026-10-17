# tracy 0.13.1 HarmonyOS (OpenHarmony PC) adaptation notes

## Status

- Branch: `feat/tracy-0.13.1`
- Task: 平台任务 tracy 0.13.1（平台 id=11270，activity 开源鸿蒙PC专项积分赛）
- Current state: recipe authored; the OHOS aarch64 cross build (Windows host,
  DevEco Studio SDK clang 15 + OHOS sysroot) completes with `conan create`
  exit code 0 — the client library is compiled from source with the two
  portability patches applied below; `test_package` is configured, compiled and
  linked against the packaged library. Execution of the test binary is done by
  CI on the native OHOS worker (the local host cannot run aarch64 OHOS ELF).

### 对话 #1
状态: built

## Upstream source note

- URL: https://github.com/wolfpld/tracy/archive/refs/tags/v0.13.1.tar.gz
- SHA256: `d4efc50ebcb0bfcfdbba148995aeb75044c0d80f5d91223aebfaa8fa9e563d2b`
- Official upstream (GitHub release tag `v0.13.1`); no mirror or fork is used.
- `cmake/version.cmake` derives the project version by parsing
  `public/common/TracyVersion.hpp` with a regex, so a GitHub archive tarball
  (which has no `.git` directory) configures fine — no `git describe` dependency.

## W0 Dependency Check

- Runtime/build dependencies: none beyond the C/C++ toolchain and libc.
- Conan dependencies: none (the recipe declares no `requires`).
- System libraries that upstream links publicly: `Threads::Threads` and
  `${CMAKE_DL_LIBS}` → resolved on OHOS by the sysroot's `libpthread.a` and
  `libdl.a`; exported through `cpp_info.system_libs = ["pthread", "dl"]`.
- Dependency split requirement: not applicable (no third-party dependency).

## Source and Build Analysis

- Build system: CMake. The root `CMakeLists.txt` defines exactly one platform
  artifact — `add_library(TracyClient ...)` from the single translation unit
  `public/TracyClient.cpp` — plus an optional Fortran binding (`TRACY_Fortran`,
  OFF) and an optional Python client (`TRACY_CLIENT_PYTHON`, OFF, which also
  requires a shared client).
- The profiler GUI is a **separate** CMake project under `profiler/` and is not
  added from the root file, so the default build needs no GLFW/X11/Wayland.
- Platform branches in the root `CMakeLists.txt` are OHOS-friendly:
  `execinfo` is only searched on FreeBSD, and `libunwind`, `debuginfod` and
  `rocprofiler-sdk` are optional (OFF / `find_package` without REQUIRED).
- `TRACY_ENABLE` defaults to ON; it is applied as a **PUBLIC** compile
  definition, i.e. consumers must also see it — `TracyC.h` starts with
  `#ifndef TRACY_ENABLE`, and without the macro the entire API degrades to
  no-op macros. The recipe therefore exports it via `cpp_info.defines`.
- Install layout: library → `lib/libTracyClient.a`; headers →
  `include/tracy/{tracy,client,common}/…`, with `INSTALL_INTERFACE include/tracy`.
  Consumers use `-I<prefix>/include/tracy` and `#include <tracy/TracyC.h>`.
- Upstream test surface (R51 inventory, verified against the v0.13.1 tarball):
  * `tests/` directory count = **1** — `test/` is an independent CMake project
    (`project(tracy-test)`, `add_executable(tracy-test test.cpp)`,
    `target_link_libraries(tracy-test TracyClient)`), vendoring only its own
    `stb_image.h` / `image.jpg`.
  * ctest/pytest registrations = **0** — the whole tree has no `add_test` /
    `enable_testing`, and the root `CMakeLists.txt` never mentions `test`
    (0 matches), so `conan create` does not build that project.
  * `test/test.cpp` is a **manual instrumentation demo**: `main()` spawns 23
    threads and then loops `for(;;)` forever, with no assertions and no success
    exit path (it only returns 2 when a SIGUSR2-triggered instrumentation failure
    path is taken). Upstream's own CI therefore only **compiles** it (the
    "Test application" step of `.github/workflows/linux.yml`, four `TRACY_*`
    flag combinations) and never runs it.
  * Consequently the number of automatable upstream cases is **0**, and the
    verification for this package is the consumer-side `test_package` that
    exercises the public C API (`upstream_test_in_build: false`,
    `upstream_tests: []` in `test_package/MANIFEST.yml`).

## Portability patches (2)

Both patches are **libc capability probes**, not platform macros, and they do not
change behaviour on glibc / Android / BSD. The OHOS sources are therefore *not*
unmodified: `conandata.yml` registers both patches and `manifest.yaml` lists them
under `patches_applied`.

1. `patches/0001-TracySystem-libc-probe-thread-cancel.patch`
   `public/common/TracySystem.cpp` guards the pthread cancellation-state calls in
   `GetThreadName()` with `#ifndef __ANDROID__`. musl — and therefore the OHOS
   libc — has **no thread cancellation at all**: `pthread_setcancelstate` is not
   declared in `<pthread.h>` and not exported by `libc.so`, so the build failed
   with `use of undeclared identifier 'pthread_setcancelstate'`. The patch
   replaces the guard with `#if defined( __GLIBC__ ) || defined( __BIONIC__ )`.
2. `patches/0002-TracyProfiler-musl-process-name.patch`
   `public/client/TracyProfiler.cpp` selects its Linux branch with
   `defined __linux__ && defined _GNU_SOURCE`, and the OHOS clang driver
   predefines `_GNU_SOURCE` **unconditionally** — verified with
   `clang++ --target=aarch64-linux-ohos --sysroot=… -dM -E -x c++`, which prints
   `#define _GNU_SOURCE 1` for both `-std=c++17` and `-std=gnu++17` (the W3 log
   line 106 also records "C++ Standard 17 with extensions OFF", i.e. the build
   itself uses `-std=c++17`). The branch is therefore taken on musl as well and
   pulls in glibc's `program_invocation_short_name` / `program_invocation_name`,
   which musl does not provide. The patch tightens the guard to
   `defined __GLIBC__` and adds a `#elif defined __linux__` branch that reads
   `/proc/self/comm` and `readlink("/proc/self/exe")`, so the process name keeps
   its real value instead of degrading to `"unknown"`.

## Recipe Notes

- `TRACY_STATIC=ON` (default, shared opt-in via `-o shared=True`), `TRACY_ENABLE=ON`,
  `TRACY_Fortran=OFF`, `TRACY_LTO=OFF`, `TRACY_CLIENT_PYTHON=OFF`.
- Toolchain/flags come from the Conan toolchain (R33): no shell compiler
  variables, no hard-coded `/usr/local` prefix, no `__OHOS__` macro injection.
- The recipe declares no conan dependencies, so W0/R36 dependency checks are
  trivially satisfied and the CI compiles only this package.
- `package_info()` exports `libs=["TracyClient"]`, `defines=["TRACY_ENABLE"]`,
  `includedirs=["include/tracy"]` and the two system libs; the package is
  static by default so consumers link the client into their own binary.

## 编译结束

- 交叉构建命令（Windows 宿主，ASCII 暂存路径见下）:
  `conan create archives/t/tracy/0.13.1 -pr:h=ohos-aarch64-windows -pr:b=default --build=missing`
- 完整日志: `reports/w3-local-ci.log`（强制重建，含 source 下载与解包、两个补丁的应用、
  `Building CXX object CMakeFiles/TracyClient.dir/public/TracyClient.cpp.obj`、
  `Linking CXX static library libTracyClient.a`、install/package 与 test_package 的
  配置、编译、链接全过程）。
- 产物: `lib/libTracyClient.a`（ELF64 AArch64）+ `include/tracy/{tracy,client,common}/**.h`
  + `licenses/LICENSE`；校验记录见 `reports/artifacts-verify.txt`。
- test_package 在桌面宿主上是交叉构建（`cross_building()` 为真），因此本机只做
  编译与链接验证，运行验证由 OHOS worker 上的原生 CI 执行。
- 路径说明：Windows 宿主上本仓库检出路径含非 ASCII 字符，mingw32-make 无法处理该
  路径下生成的 Makefile，故本地 W3 在与归档逐字节相同的 ASCII 暂存路径
  （`C:\ohc\tracy\0.13.1`）运行 `conan create`。
- 权威验证：平台 CI 在**原生 OHOS worker** 上以 `-pr:h=ohos-aarch64 -pr:b=ohos-aarch64`
  构建（build == host ⇒ `cross_building()` 为假 ⇒ test_package 由 `self.run` 真实执行）。
  构建 **#50906、#50909、#50916、#50929 与 #50931** 均为 `## CI 校验通过`
  （`Conan test_package: 通过`、L0 结构门禁通过、L1 测试执行验证通过）；其中 **#50931**
  对应当次推送的提交 `5a6317ea2`。上述构建号均为历史值：CI 为**评论触发**（push 不触发），
  需在 PR 上发 `/rebuild` 才会重跑，故引用时应以平台最新 `## CI 校验通过` 评论为准，
  不要沿用本行历史构建号。
