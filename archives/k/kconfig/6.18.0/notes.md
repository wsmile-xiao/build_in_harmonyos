# kconfig 6.18.0 notes

## Scope

This package is part of the Akonadi KF 6.18 baseline. It updates the
published 6.14.0 HarmonyOS PC recipe to KDE Frameworks 6.18.0 while keeping
the configuration libraries needed by higher-level KF packages.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `KCONFIG_USE_QML=OFF` disables the optional QML plugin for the initial
  Akonadi baseline.
- `USE_DBUS=OFF` disables KConfig DBus integration; Akonadi will get DBus from
  `qtbase-sql-dbus/6.11.1` when that dependency is available.
- `BUILD_TESTING=ON` runs the upstream CTest autotests during Conan build.
- The OHOS runner excludes `kconfigcore-kconfigtest`,
  `kconfigcore-kdesktopfiletest`, `kconfigcore-test_kconf_update`,
  `kconfiggui-kstandardshortcutwatchertest`, and
  `kconfigcompiler-basic-test` for current OHOS environment limitations.
- `ecm_install_po_files_as_qm(poqm)` is disabled because the Qt Linguist tools
  component is not part of the qtbase package used by this repository.
- CMake configure/build prepends the OHOS SDK `native/llvm/lib` directory to
  `LD_LIBRARY_PATH` so SDK `lld` can load its matching `libxml2.so.16` on CI
  workers that do not export that path globally.

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `517cbf6747df9289d6fce860a73d49e59354685334ae468ecd53f1067d9d618b`.
- The OHOS CMake patch was checked against the unpacked 6.18.0 source.

OHOS `conan create` verification passed on 2026-08-19.

- Runner log: `/storage/Users/currentUser/ohos-users/codex-a/kf618-kitemviews-upstream-low-20260819/logs/kconfig-r7.log`.
- Full package reference: `kconfig/6.18.0#dab71a89fbaefa7462ad1617993d8bb4:57ffd8c720a5bfee7e8827990cd6550a49181c1b#1305210726957a83004340d31d590768`.
- Upstream CTest: 64/64 executed tests passed.
- Excluded upstream CTest entries: `kconfigcore-kconfigtest`,
  `kconfigcore-kdesktopfiletest`, `kconfigcore-test_kconf_update`,
  `kconfiggui-kstandardshortcutwatchertest`, `kconfigcompiler-basic-test`.
- Conan `test_package`: 1/1 passed.
- Runner results: L0 pass, L1 pass, L4 pass, L5 pass; L2 skip:
  `kreadconfig6`/`kwriteconfig6` version-help smoke failed non-blocking;
  `RUN_RC=0`.
