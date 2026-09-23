# kservice 6.26.0 notes

## Scope

This package is part of the KF6 6.26 baseline (platform task #6330). It
updates the existing HarmonyOS PC recipe from 6.18.0 to KDE Frameworks
6.26.0 (version follow-up mode; same OHOS adaptation set as 6.14.0/6.18.0).

## Upstream verification

- Upstream tag `v6.26.0` verified via
  `git ls-remote https://invent.kde.org/frameworks/kservice.git`:
  `refs/tags/v6.26.0` -> commit `e422dcdb85b369c04fac849f58e15d788d403eb4`
  (annotated tag object `e841de7efbb0459dc439060c632c734d4989ee4e`).
- Official tarball
  `https://download.kde.org/stable/frameworks/6.26/kservice-6.26.0.tar.xz`
  HEAD-probed (302 to KDE mirrors) and downloaded; SHA-256 verified:
  `f8528524ccafb6a495962dd3260c442377920169f1c444f11657ea42558a53b6`.

## Upstream CMakeLists.txt dependency check (6.26.0)

- `cmake_minimum_required(VERSION 3.29)` (raised from 3.16 in 6.18.0).
- `find_package(ECM 6.26.0 NO_MODULE)` — satisfied by `ecm/6.26.0`
  (tool_requires, published on ohpcd).
- `REQUIRED_QT_VERSION 6.9.0`, `find_package(Qt6 ... REQUIRED Xml)` —
  satisfied by `qtbase/6.11.1` (components Core/Xml unchanged).
- `KF_DEP_VERSION "6.26.0"`: `find_package(KF6Config/KF6CoreAddons/KF6I18n
  6.26.0 CONFIG REQUIRED)` — all three published on ohpcd at 6.26.0
  (W0 verified 2026-09-09 via `conan download --only-recipe`).
- `KF6DocTools` optional (disabled via
  `CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=ON`).
- Deprecation allowlist: `ecm_set_disabled_deprecation_versions(QT 6.11.0
  KF 6.23.0)`; no deprecation warnings hit the error boundary.

## Upstream changes 6.18.0 -> 6.26.0 (relevant to the OHOS adaptation)

- `cmake_minimum_required` raised from 3.16 to 3.29 (local cmake 4.1.2 and
  the CI toolchain satisfy this).
- Minimum Qt version raised to 6.9.0; `qtbase/6.11.1` satisfies it.
- `KF_DEP_VERSION` raised to 6.26.0 for KF6Config/KF6CoreAddons/KF6I18n;
  all satisfied by published ohpcd packages.
- Upstream CTest registration unchanged: autotests/ still registers
  ksycocatest, ksycoca_xdgdirstest, ksycocathreadtest, kservicetest,
  kapplicationtradertest, kmimeassociationstest (6 entries on non-WIN32).
  tests/ helper executables (kservicegroup_dumper, findservice,
  kmimeassociations_dumper) remain ecm_mark_as_test manual helpers, not
  CTest entries.
- `testNonReadableSycoca` and `extraFileInFutureShouldRebuildSycocaOnce`
  implementations are unchanged, so the 6.18.0 OHOS FS-sensitive guard
  patch applies cleanly (verified with `git apply --check`).

## Adaptations (inherited from 6.18.0, verified against 6.26.0 source)

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for
  OHOS.
- `KF_SKIP_PO_PROCESSING=ON` avoids translation catalog generation.
- `BUILD_PYTHON_BINDINGS=OFF` avoids Shiboken/PySide requirements.
- `CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=ON` keeps optional docs out of
  the baseline package.
- `BUILD_TESTING=ON` enables the upstream CTest/autotests suite during the
  OHOS Conan package build.
- Runtime/build dependencies: `qtbase/6.11.1`, `kconfig/6.26.0`,
  `kcoreaddons/6.26.0`, `ki18n/6.26.0`; build dependency `ecm/6.26.0`.
- A minimal test-only MIME database is generated under the build folder and
  exposed through `XDG_DATA_DIRS`. It provides both
  `mime/packages/freedesktop.org.xml` for `QMimeDatabase` and per-type
  `mime/<type>.xml` entries for `KBuildMimeTypeFactory`, which is required
  by upstream service-trader and MIME association autotests on the current
  runner.
- `patches/0001-autotests-guard-ohos-fs-sensitive-checks.patch` guards two
  `ksycocatest` subtests behind the recipe-defined
  `KSERVICE_OHOS_SKIP_UNSUPPORTED_FS_TESTS=1` environment variable
  (identical to the 6.18.0 baseline patch; both subtests skip only when
  the OHOS runner's filesystem behaviour makes the upstream precondition
  false: WriteOwner-only sycoca stays readable; future-file mtime does not
  strictly advance).
- ECM 6.26 KDEInstallDirs6 runs the qtbase qtpaths host tool during
  configure; the sandbox LD_LIBRARY_PATH contains an incompatible
  libc++_shared.so which shadows the compatible one, so `/system/lib64`
  (and the SDK `llvm/lib` dir, E132 lld libxml2.so.16) is prepended during
  configure and ctest (kconfig 6.26.0 / bluez-qt 6.28.0 / kcrash 6.26.0
  precedent).

## Verification

OHOS `conan create` verification passed on 2026-09-09.

- Command: `conan create archives/k/kservice/6.26.0
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=default --build=missing` ->
  rc=0.
- Runner log: `reports/conan-create.log`.
- Upstream CTest passed 6/6 inside conan create: `100% tests passed, 0
  tests failed out of 6` (ksycocatest, ksycoca_xdgdirstest,
  ksycocathreadtest, kservicetest, kapplicationtradertest,
  kmimeassociationstest).
- `ksycocatest` totals in `Testing/Temporary/LastTest.log`: 8 passed, 0
  failed, 2 skipped (the two guarded OHOS FS-sensitive subtests).
- Conan `test_package` passed 1/1 and printed
  `PASS: KService temporary service OK`.
- Main binary package id: `08ff486632bbe8da1a11f30478317fb8c06bc5a1`.

## Upstream Tests Not Run

- `tests/kservicegroup_dumper`, `tests/findservice`, and
  `tests/kmimeassociations_dumper` were built, but upstream marks them with
  `ecm_mark_as_test()` and does not register them as CTest entries; they
  are manual helper executables, not part of the upstream CTest run.
- The AppStream metadata check was not set up because the current OHOS
  runner does not provide `appstreamcli`.
- Python bindings were not built or tested because
  `BUILD_PYTHON_BINDINGS=OFF`; those bindings require Shiboken/PySide and
  are outside this C++ baseline package.
- KF6DocTools documentation generation was not built because the recipe
  sets `CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=ON`; docs are optional and
  not part of the runtime package verification.

## Upstream Test Guards

- `KSycocaTest::testNonReadableSycoca` is skipped only when
  `KSERVICE_OHOS_SKIP_UNSUPPORTED_FS_TESTS=1` and the current runner can
  still open a sycoca file after it has been set to `QFile::WriteOwner`.
  The test is intended to simulate an unreadable/root-owned cache file;
  that precondition is false on this runner.
- `KSycocaTest::extraFileInFutureShouldRebuildSycocaOnce` is skipped only
  when `KSERVICE_OHOS_SKIP_UNSUPPORTED_FS_TESTS=1` and the rebuilt sycoca
  timestamp does not become strictly newer than the old timestamp. The
  current runner's filesystem timestamp behavior does not satisfy that
  strict mtime precondition for this subtest.
