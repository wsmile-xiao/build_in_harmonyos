# kwidgetsaddons 6.26.0 notes

## Scope

This package is part of the KF6 6.26 baseline (task #6326, dependency chain:
extra-cmake-modules 6.26.0 + qtbase 6.11.1). It updates the existing
HarmonyOS PC recipe from 6.18.0 to KDE Frameworks 6.26.0.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_PYTHON_BINDINGS=OFF` is still required for 6.26.0 because the
  upstream CMakeLists keeps the option defaulting to ON (it is only auto-off
  for ANDROID/APPLE/WIN32/HAIKU or static builds) and Python bindings would
  otherwise try to discover Shiboken6/PySide6.
- `BUILD_DESIGNERPLUGIN=OFF` avoids Qt6UiPlugin/Qt Designer plugin discovery.
- `BUILD_TESTING=ON` runs the upstream CTest autotests during Conan build.
- The OHOS headless runner excludes `ktooltipwidgettest` and
  `kwidgetsaddons-kcolumnresizertest`: the first hangs under the offscreen
  platform plugin, the second asserts native layout geometry that differs
  under offscreen (6.18.0 precedent; still present in 6.26.0).
- `ecm_install_po_files_as_qm(poqm)` is disabled by patch because the Qt
  Linguist tools component is not part of the qtbase package used by this
  repository.
- ECM 6.26 KDEInstallDirs6 runs the qtbase `qtpaths` host tool during
  configure (ecm_query_qt -> QT_INSTALL_PREFIX); the sandbox LD_LIBRARY_PATH
  contains an incompatible libc++_shared.so which shadows the compatible
  one, so `/system/lib64` and the qtbase lib dir are prepended
  (kconfig 6.26.0 / bluez-qt 6.28.0 / kitemviews 6.26.0 precedent).

## Upstream changes 6.18.0 -> 6.26.0

- `cmake_minimum_required` raised 3.16 -> 3.29 (local cmake 4.1.2 satisfies;
  ECM 6.26.0 already requires 3.29 and is published on ohpcd, so the CI
  cmake satisfies it too).
- `REQUIRED_QT_VERSION` raised 6.7.0 -> 6.9.0 (qtbase 6.11.1 satisfies).
- New upstream autotest `kactionmenutest` (26 CTest entries total).
- Source diff otherwise limited to poqm translations and minor autotest
  touch-ups; no changes to the OHOS adaptation surface.

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `65044882e30b305fe9fb20331a354cd811ca9d80b5c7f9fa722639f3334fe630`
  (downloaded tarball matches download.kde.org .sha256 file).
- The po/qm patch was verified to apply cleanly against the unpacked 6.26.0
  source with patch_ng (the same engine conan uses); the only upstream change
  near the patch context is the Qt deprecation version line (6.10 -> 6.11).

OHOS `conan create` verification passed on 2026-09-05.

- Full package reference:
  `kwidgetsaddons/6.26.0#d1f13c6c084d326c2c6bce1302f810f3:57ffd8c720a5bfee7e8827990cd6550a49181c1b#54b247a86cff100994e4b9e7acab1ea1`.
- Upstream CTest: 24/24 executed tests passed (26 entries total; excluded
  `ktooltipwidgettest` and `kwidgetsaddons-kcolumnresizertest` for OHOS
  headless/offscreen limits — same exclusions as 6.18.0).
- New 6.26.0 autotest `kactionmenutest` passed (Test #2).
- Conan `test_package`: 1/1 passed (`PASS: KPageWidgetModel addPage/rowCount
  OK (rows=1)`).
- Log: `~/tmp/kw-conan-create-logs/create.log`.
---

**编译结束**: 2026-09-05 21:48
**最终状态**: built

## Submit 流程记录

- W3 本地 CI 模拟通过（`reports/w3-local-ci.log`：G0/G0e/L0i/L0j/L0k/L0m/KC/JC 全绿，
  conan create 复跑通过）。
- W4 独立审计通过（`reports/audit-result.json`：P0=0 P1=0，verdict=pass）。
- packaging/ 已生成 release + debug tar.gz（本地交付物，gitignore 不入 PR）。
- PR body 模板已填写（`reports/pr-body.md`，积分赛模板 + 实测数据）。
