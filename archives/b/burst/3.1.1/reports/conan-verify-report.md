# Conan Verify Report — burst 3.1.1

**Verdict**: FAIL (`-fsigned-char` fix pending remote rerun)
**Reference**: `burst/3.1.1@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-09-09T03:21:39.388780

> Post-run note: the E092 pre-build warning below was subsequently addressed in both recipe toolchains by selecting CMake's Linux platform model for the platform-neutral OHOS build. G2 stopped earlier because the configured OHOS compiler path is absent on this macOS host, so a runner rerun is still required.

## G0: ✅ PASS
**Knowledge hit**: E092
  📦 构建系统: cmake
  ⚠️ 已知风险 E092 未在配方中处理
     根因: CMake 不认识 HarmonyOS 作为目标平台，
没有对应的 platform module。
当 CMake 检测到系统名称为 harmonyos/ohos 时，
无法匹配任何已知平台（Linux, Darwin, Windows
     方案: cmake-toolchain
     修复: cmake -B build -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=
     ⚡ G2 conan create 可能因此失败，建议先修复

## G1: ✅ PASS
  ✅ name 声明
  ✅ version 声明
  ✅ source() 方法
  ✅ build() 方法
  ✅ package() 方法
  ✅ package_info() 方法
  ✅ export_sources() 方法
  ✅ 补丁应用调用
  ℹ️ R26: 未检测到静态链接配置（非系统同名库无需静态）
  ✅ conandata.yml 完整
  ✅ test_package/ 存在 (R28)
  ✅ test_package/MANIFEST.yml 存在

## Local G2: ❌ ENVIRONMENT UNAVAILABLE
**Knowledge hit**: E540
  ❌ conan create failed before compilation:
     the OHOS profile selects `/data/service/hnp/bin/clang++`, but that
     compiler path does not exist on the current Apple arm64 host.
    🧠 知识图谱命中: E540 (评分:3328)
     根因: The OHOS Conan profile can point CC/CXX to /data/service/hnp/bin/clang, so configure succeeds, while later recipe comman
     方案: runner-path-prepend
     命令: EXTRA_PATH=/data/service/hnp/bin:/data/service/hnp/cmake.org/cmake_4.1.2/bin:$HOME/usr/local/bin:$HOME/.local/bin:$HOME/
     文档: knowledge/drafts/zlib-shadow-ci-hnp-tool-path.md

## Remote OHOS CI #43824

**Historical result**: ❌ FAIL before test execution

- OHOS 6.0 armv8 compiler discovery: PASS
- Boost 1.90.0 and doctest 2.5.2 resolution: PASS
- CMake configure/generate: PASS
- 96 upstream test translation units: compiled
- `burst-unit-tests`: linked
- `check` execution: FAIL, `/bin/sh: burst-unit-tests: inaccessible or not found` (exit 127)

`CMAKE_SYSTEM_NAME=Linux` caused CMake to mark the on-device OHOS armv8 build as cross-compiling. In that mode, upstream `add_custom_target(check ALL COMMAND burst-unit-tests ...)` was emitted as a bare command rather than the executable target path. The recipe now builds `burst-unit-tests` explicitly and executes its absolute path with upstream's original doctest arguments. This leaves CMake's cross-build model intact, keeps all 724 cases enabled, and removes dependence on custom-target command rewriting. A new `/rebuild` is required for final verification.

## Remote OHOS CI #45099

**Result**: ❌ 723/724 upstream cases; signed-char fix pending

- Absolute-path executable launch: PASS
- Upstream doctest cases: 723 passed, 1 failed, 0 skipped
- Upstream assertions: 1,035 passed, 1 failed
- Sole failure: `to_unsigned<char>` expected 128 for zero but received 0
- `test_package`: not reached because Conan correctly stopped on the upstream failure

OHOS AArch64 defaults plain `char` to unsigned. The unchanged upstream test explicitly includes plain `char` in its signed-type matrix, so its expected midpoint mapping requires signed-char compilation. The recipe now adds `-fsigned-char` for the OHOS upstream-suite build, following knowledge E419. No upstream test is patched, suppressed, or removed; a new `/rebuild` is required for final verification.

## Clean native lifecycle after the fix

**Result**: ✅ PASS

- Conan: 2.32.0 with a new isolated Conan home
- Test command: absolute `build/Release/test/burst-unit-tests --report_level=short --color_output`
- Upstream doctest: 724/724 cases, 1,036/1,036 assertions
- Package creation and installation: PASS (185 headers)
- Packaged consumer: 4/4 scenarios, 6/6 explicit checks
