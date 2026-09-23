# kcrash 6.26.0 notes

## Scope

This package is part of the KF6 6.26 baseline (task #6328, dependency chain:
extra-cmake-modules 6.26.0 + kconfig/kcoreaddons/ki18n 6.26.0, qtbase
6.11.1). It updates the existing HarmonyOS PC recipe from 6.18.0 to KDE
Frameworks 6.26.0.

## Upstream changes 6.18.0 -> 6.26.0 (relevant to the OHOS adaptation)

- `cmake_minimum_required` raised from 3.16 to 3.29 (local cmake 4.1.2 and
  the CI toolchain satisfy this).
- Minimum Qt version raised from 6.7.0 to 6.9.0; `qtbase/6.11.1` satisfies
  it. Required Qt components unchanged (Core, Gui; Qt6Test for
  BUILD_TESTING=ON).
- `KF_DEP_VERSION` raised to 6.26.0 for KF6CoreAddons; satisfied by
  `kcoreaddons/6.26.0`.
- Deprecation allowlist raised: `ecm_set_disabled_deprecation_versions(QT
  6.11.0 KF 6.23.0)` (was 6.10.0/6.17.0). No deprecation warnings hit the
  error boundary with ecm/6.26.0.
- New crash-handler feature: `KCRASH_CRASH_IN_HANDLER` environment variable
  consumed by `src/kcrash.cpp` (static `s_crashInHandler`), used by the new
  upstream autotest `testPartialMetadata` inside the `kcrashtest` suite
  (CTest entry count stays at 3: kcrashtest, coreconfigtest, metadatatest).
- New upstream autotest `KCrashTest::testPartialMetadata` (plus shared
  metadata-file path switch when `QStandardPaths::isTestModeEnabled()`):
  the executed upstream CTest count grows from 3 to 4.
- X11 code path unchanged in shape (`WITH_X11` option defaults ON for
  "UNIX && !APPLE && !ANDROID && !HAIKU"); `HAVE_X11` stays OFF on OHOS via
  `WITH_X11=OFF` passed in the recipe toolchain (same behavior as the
  6.14/6.18 builds, now explicit).

## Adaptations (inherited from 6.18.0, verified against 6.26.0 source)

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for
  OHOS.
- `BUILD_DESIGNERPLUGIN=OFF` avoids Qt6UiPlugin/Qt Designer plugin
  discovery.
- `WITH_X11=OFF` disables X11 integration: upstream defaults it to ON for
  "UNIX && !APPLE && !ANDROID && !HAIKU" and HarmonyOS matches that branch
  (CMAKE_SYSTEM_NAME=HarmonyOS is not Android), but OHOS has no X11
  headers/libs, so `find_package(X11 REQUIRED)` would fail. The 6.14/6.18
  builds resolved X11 off via the cross-compiling environment; 6.26.0 makes
  it explicit in the recipe.
- `BUILD_TESTING=ON` enables the upstream CTest/autotests suite during the
  OHOS Conan package build.
- ECM 6.26 KDEInstallDirs6 runs the qtbase `qtpaths` host tool during
  configure; the sandbox LD_LIBRARY_PATH contains an incompatible
  libc++_shared.so which shadows the compatible one, so `/system/lib64` is
  prepended during configure and ctest (kconfig 6.26.0 / bluez-qt 6.28.0
  precedent).
- No source patch is required for 6.26.0: the 6.18.0 recipe applied no
  patches and the only build-relevant upstream deltas are version bumps
  plus features that stay inside the existing adaptation set.

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `d05d93863a745ce0d4ab8ccff684a84a813ee4cbcc68c9c7a5175107b107e931`.
- Upstream tag existence verified: `git ls-remote --tags
  https://invent.kde.org/frameworks/kcrash.git` shows `v6.26.0` at commit
  `411aa2ed63a881d5ade82331fbf90f301f3386ce` (annotated tag object
  `593f44b698ac56a7037f23abf255fab3dfbc6f4e`).

OHOS `conan create` verification passed on 2026-09-05:

- Runner log: `reports/conan-create.log` + `reports/w3-local-ci.log`.
- Full package reference:
  `kcrash/6.26.0#897d68f7bf06e2266e3c7231261c0198:0ac31baf2280e058baca76c037388fe82e2b86fb`.
- W3 local CI simulation (setup.sh + build_and_test.sh): L0 pass, L1 pass,
  L2 skip (no bin/ dir), L4 pass, L5 pass.
- Upstream CTest passed 3/3: `kcrashtest` (4.03s, includes the 6.26
  `testPartialMetadata` crash-injection case), `coreconfigtest`, and
  `metadatatest`.
- Conan `test_package` passed 1/1 with a `KCrash::setDrKonqiEnabled(false)`
  consumer compile/link/runtime smoke.

---

**编译结束**: 2026-09-05 21:45
**最终状态**: built
