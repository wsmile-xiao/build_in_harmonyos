# kconfig 6.26.0 notes

## Scope

This package is part of the Akonadi KF baseline refresh. It updates the
published 6.18.0 HarmonyOS PC recipe to KDE Frameworks 6.26.0 while keeping
the configuration libraries needed by higher-level KF packages. The 6.18.0
recipe was used verbatim as the starting point (base recipe).

## Upstream changes 6.18.0 -> 6.26.0 (relevant to the OHOS adaptation)

- `cmake_minimum_required` raised from 3.16 to 3.29 (local cmake 4.1.2 and CI
  toolchain satisfy this).
- Minimum Qt version raised from 6.7.0 to 6.9.0; `qtbase/6.11.1` satisfies it.
- New required autotest dependency `Qt6::CorePrivate` when Qt >= 6.10
  (`find_package(Qt6CorePrivate ... EXACT)` plus `Qt6::CorePrivate` in
  `ecm_add_tests` link libraries). qtbase/6.11.1 ships `Qt6CorePrivate`
  CMake config, so no extra requirement was needed.
- Test naming was reworked: explicit `NAME_PREFIX kconfigcore-`/
  `kconfiggui-` arguments and `TEST_NAME kconfigcore-...` literals were
  replaced by the `ECM_TEST_NAME_PREFIX` variable (supported since ECM
  6.22.0; ecm/6.26.0 in this repo implements it). Effective test names are
  unchanged (`kconfigcore-*`, `kconfiggui-*`, `kconfigcompiler-*`), so the
  6.18.0 OHOS test exclusion list still matches.
- New upstream autotests: `kconfigcore-qiodevicetest`,
  `kconfigcore-parsetest`, `kconfigcompiler-test_kconfigconstructor` (+ its
  `_cmake` variant), so the executed test count grows compared to 6.18.0's
  64/64 baseline.
- New `BUILD_FUZZERS` subdirectory (autotests/ossfuzz) - off by default, not
  built.
- `kconfiginibackendreader_p.h` added to src/core (internal refactor, no
  recipe impact).

## Patch applicability (6.18.0 patch vs 6.26.0 source)

The 6.18.0 `0001-CMakeLists.txt.patch` does NOT apply to 6.26.0
(`patch -p1 --dry-run` fails: Hunk 1 FAILED 69/69, Hunk 2 FAILED 72/77;
only the test-library hunk and the two QML guard hunks apply). Root causes:

- The top-level CMakeLists.txt now has the new `BUILD_FUZZERS` block above
  `include (ECMPoQmTools)`, shifting line numbers so the poqm hunk no longer
  matches.
- The `kconfig_compiler_test()` function signature block moved, so the
  `target_link_libraries` hunk context no longer matches.

The patch was therefore regenerated for 6.26.0. Hunk semantics inherited
from 6.18.0:

1. Comment out `ecm_install_po_files_as_qm(poqm)` (Qt6LinguistTools not
   published to ohpcd).
2. Make the `kconfig_compiler_test()` link libraries conditional:
   `Qt6::Test KF6::ConfigGui` plus `Qt6::Qml` only when `KCONFIG_USE_QML`.
3. Guard `Test14`-`Test17` (QML_REGISTRATION) with `if(KCONFIG_USE_QML)`.
4. Guard the `test14qml`-`test17qml` executables block with
   `if(KCONFIG_USE_QML)`.

New in the 6.26.0 patch (not needed for 6.18.0):

5. In `autotests/CMakeLists.txt`, move `kconfigtest.cpp` out of
   `ecm_add_tests(...)` into an `if(NOT HARMONYOS)`-guarded
   `ecm_add_test`, because the 6.26.0 test source uses C++20 chrono
   calendar types that the OHOS toolchain (clang 15 / libc++ / cppstd=17)
   cannot compile; also guard the matching `set_tests_properties` call.

## Adaptations (inherited from 6.18.0)

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `KCONFIG_USE_QML=OFF` disables the optional QML plugin for the initial
  Akonadi baseline.
- `USE_DBUS=OFF` disables KConfig DBus integration; Akonadi will get DBus from
  `qtbase-sql-dbus/6.11.1` when that dependency is available.
- `BUILD_TESTING=ON` runs the upstream CTest autotests during Conan build.
- The OHOS runner excludes `kconfigcore-kconfigtest`,
  `kconfigcore-kdesktopfiletest`, `kconfigcore-test_kconf_update`,
  `kconfiggui-kstandardshortcutwatchertest`, and
  `kconfigcompiler-basic-test` for current OHOS environment limitations
  (same exclusion set as 6.18.0; test names are stable across the two
  releases thanks to the ECM_TEST_NAME_PREFIX mechanism).
- `ecm_install_po_files_as_qm(poqm)` is disabled because the Qt Linguist tools
  component is not part of the qtbase package used by this repository.
- CMake configure/build prepends the OHOS SDK `native/llvm/lib` directory to
  `LD_LIBRARY_PATH` so SDK `lld` can load its matching `libxml2.so.16` on CI
  workers that do not export that path globally.

## Adaptation issues hit during this port (6.26.0-specific)

Two new issues were hit compared to 6.18.0, both fixed in the recipe:

1. **ECM 6.26 `KDEInstallDirs6` now requires a working `qtpaths` at
   configure time** (`ecm_query_qt` -> `QT_INSTALL_PREFIX`, non-TRY). The
   qtbase `qtpaths` host tool failed to start because the sandbox
   `LD_LIBRARY_PATH` contains an incompatible `libc++_shared.so` under
   `/data/storage/el1/bundle/libs/arm64` that shadows the compatible one.
   Fix: `_cmake_build_env()` prepends `/system/lib64` (compatible
   `libc++_shared.so`) ahead of the sandbox entries - bluez-qt 6.28.0
   precedent.
2. **`kconfigtest.cpp` (6.26.0) uses `std::chrono` calendar types
   (`days`/`weeks`/`months`/`years`, C++20 chrono) at lines 109-112/2268+**;
   this code is new in 6.26.0 (absent from 6.18.0). The OHOS libc++ headers
   available to clang 15 with cppstd=17 do not provide these types, so the
   `kconfigtest` target cannot compile. Since this test was already on the
   OHOS exclusion list (excluded at run time in 6.18.0), the patch now also
   skips building the target on HarmonyOS: the target is moved out of
   `ecm_add_tests(...)` into an `if(NOT HARMONYOS)` block (plus the
   `set_tests_properties` reference). `HARMONYOS` is a plain variable
   injected by the recipe toolchain (`tc.variables["HARMONYOS"] = "1"` when
   `settings.os == "OHOS"`); CMake's `CMAKE_SYSTEM_NAME` on this target is
   `HarmonyOS` but it does not define an `HARMONYOS` variable by itself.
3. The same sandbox libc++ shadowing issue also broke **all 68** upstream
   test executables at run time (loader could not resolve `_Unwind_Resume`
   / `__cxa_*` symbols). Fix: `_run_upstream_tests()` prepends
   `/system/lib64` to the ctest environment as well.

## Verification

Initial local checks:

- Upstream source SHA256 verified against the official
  `kconfig-6.26.0.tar.xz.sha256`:
  `8bb5aa918d8e60ec140a33db3c329414d2319dc97a1644b368da5576125c92b5`.
- The regenerated OHOS CMake patch applies cleanly (`patch -p1` dry-run and
  real run) to a pristine unpacked 6.26.0 source tree.
- W0 dependency probe (R35, conan download): `qtbase/6.11.1` and `ecm/6.26.0`
  recipes exist in the ohpcd remote.

OHOS `conan create` verification passed on 2026-09-03.

- Command: `conan create . -pr:h ~/.conan2/profiles/ohos-aarch64
  -pr:b ~/.conan2/profiles/ohos-aarch64 --build=missing`
- Package reference: `kconfig/6.26.0` (package id
  `57ffd8c720a5bfee7e8827990cd6550a49181c1b`).
- Upstream CTest: **68/68 executed tests passed, 0 failed**
  (`100% tests passed, 0 tests failed out of 68`), executed with
  `BUILD_TESTING=ON` inside `conan create` (upstream autotests +
  kconfig_compiler tests). Compared to 6.18.0's 64/64, the executed count
  grew by 4 because 6.26.0 adds upstream tests
  (`kconfigcore-qiodevicetest`, `kconfigcore-parsetest`,
  `kconfigcompiler-test_kconfigconstructor` + `_cmake` variant) while the
  `kconfigtest` target is now skipped at build time (previously excluded at
  run time only).
- Excluded upstream CTest entries (5, same set as 6.18.0):
  `kconfigcore-kconfigtest`, `kconfigcore-kdesktopfiletest`,
  `kconfigcore-test_kconf_update`, `kconfiggui-kstandardshortcutwatchertest`,
  `kconfigcompiler-basic-test`. With 6.26.0, `kconfigcore-kconfigtest` is
  additionally skipped at build time (C++20 chrono calendar types not
  available with clang 15 / libc++ / cppstd=17 on OHOS).
- Conan `test_package`: 1/1 passed
  (`PASS: KConfig group round-trip OK (name=world)`).
- Package artifacts: `lib/libKF6ConfigCore.so`, `lib/libKF6ConfigGui.so`,
  `lib/cmake/KF6Config/`, `include/`, `bin/` (kreadconfig6/kwriteconfig6/
  kconf_update host tools installed).
---

**编译结束**: 2026-09-03 01:25
**最终状态**: built
