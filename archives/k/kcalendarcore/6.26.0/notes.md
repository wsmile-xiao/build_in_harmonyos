# kcalendarcore 6.26.0 notes

## Scope

New KF6 port of kcalendarcore for HarmonyOS PC (no older version of this
library existed in the repo). The recipe follows the 6.26.0-generation KF6
recipe shape proven by kconfig 6.26.0 / kitemviews 6.26.0 (KF_IGNORE_PLATFORM_CHECK,
ECM_MODULE_PATH injection, manual conan_cmakedeps_paths.cmake,
/system/lib64 LD_LIBRARY_PATH prepend, offscreen headless tests).

## Upstream dependency structure (verified from the 6.26.0 source)

- `find_package(Qt6 6.9.0 CONFIG REQUIRED Core Gui)` — qtbase/6.11.1 OK.
- `find_package(LibIcal 3.0)` with `TYPE REQUIRED` and the project's own
  `cmake/FindLibIcal.cmake` module-mode finder — libical/4.0.1 in ohpcd
  (VERSION "4.0" PATCH (1) parsed from ical.h satisfies >= 3.0).
- `find_package(ECM 6.26.0 NO_MODULE REQUIRED)` — ecm/6.26.0 OK.
- **No** dependency on kconfig / kcoreaddons / kholidays in the 6.26.0
  CMakeLists.txt (kholidays is not referenced at all; the task brief was
  based on an incorrect dependency map).
- `BUILD_TESTING` requires Qt6Test — shipped by qtbase/6.11.1.

## OHOS adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` — standard KF6 bypass of the KDE platform
  allowlist.
- `USE_QML=OFF` — the QML plugin (`src/qml`, `option(USE_QML ... ON)` by
  default) needs Qt6Qml which is not part of the qtbase ohpcd package.
- `BUILD_PYTHON_BINDINGS=OFF` — upstream default ON; it is auto-disabled
  only for ANDROID/APPLE/WIN32/HAIKU or static builds, so OHOS needs the
  explicit opt-out (Shiboken6/PySide6 unavailable).
- No po/qm patch needed: the 6.26.0 tarball ships no po/ or poqm/ directory
  and the top-level CMakeLists.txt has no `ecm_install_po_files_as_qm`
  call (verified by grep).
- `PERL_EXECUTABLE` is injected from the `perl/5.42.2` tool_requires
  package; 461 of the ~507 registered CTest entries are data-driven tests
  that invoke `autotests/runsingletestcase.pl` (perl + `diff`, both
  available in the build/test environment).
- Timezone data for the test run comes from the `tzdata/2026.3` conan
  package (a standard TZif zoneinfo tree): OHOS ships no
  `/usr/share/zoneinfo`, and without a TZif database Qt logs "Unable to
  determine system time zone" and the affected upstream tests fail
  (verified: testincidence went from 15 passed/1 failed to 16/16 once
  TZDIR was set). The recipe exports `TZDIR` (musl localtime_r + Qt unix
  TZ backend read it) and `QT_ZONEINFO` (Qt named-zone lookup) pointing
  at the package's `lib/python3.12/site-packages/tzdata/zoneinfo` tree,
  plus `TZ=UTC` for determinism. Three tests whose expectations embed
  timezone-database snapshots (testicaltimezones write(),
  Compat-AppleICal_1.5.ics, XCalIn-rfc6321-b-2-2.xcal) still differ from
  the tzdata 2026.3 representation and are excluded (see Test results);
  the upstream sources themselves document this class of OS/timezone-data
  dependent divergence (testicaltimezones.cpp comments about FreeBSD
  spurious transitions).
- libical 4.0.1 ships OHOS relative sonames (`./libical.so`): the musl
  loader resolves DT_NEEDED entries containing a slash from the process
  CWD, not from LD_LIBRARY_PATH. All upstream CTest entries run with
  CWD = <build>/autotests, so the recipe drops copies of the libical
  libraries into that directory (and the build root) before ctest
  (`_prepare_ctest_runtime_links`, libical recipe precedent).
- Standard KF6 recipe plumbing (same as kconfig/kitemviews 6.26.0):
  ECM_MODULE_PATH variable injection, manually written
  `conan_cmakedeps_paths.cmake` (qtbase and libical use
  cmake_find_mode=none so CMakeDeps does not export their prefix),
  `/system/lib64` prepended ahead of the sandbox libc++_shared.so shadow,
  `QT_QPA_PLATFORM=offscreen` + XDG sandbox dirs for the test run.

## Test plan

- Upstream CTest runs inside `conan create` with `BUILD_TESTING=ON`:
  505 registered entries = 44 unit test executables (43 via
  macro_unit_tests + testicaltimezones on non-MSVC) + 461 data-driven
  entries (RecurNext/RecurPrev/RecursOn over 144 RecurrenceRule .ics
  fixtures = 432, plus Compat 8 / VCalIn 13 / XCalIn 8 format
  round-trips, libicalV4 variants since LibIcal_VERSION 4.0.1 >= 3.99.99).
- `test_package` exercises MemoryCalendar/Event/Todo creation and an
  ICalFormat toString/fromString round-trip (real libical-backed parse).
- Execution result: `100% tests passed, 0 tests failed out of 502`
  (3 tzdata-snapshot-sensitive entries excluded, reasons per test in
  reports/test-report.md).

## Verification

- Source SHA256 verified:
  `386be0eee392d8432b6b7fafd3dead95dd1fc74f81790928c580f81e6222a17c`
  (downloaded from download.kde.org).
- W0 dependency probe (R35, conan download): qtbase/6.11.1,
  libical/4.0.1, tzdata/2026.3, ecm/6.26.0, perl/5.42.2 recipes +
  binaries exist in the ohpcd remote.
- OHOS conan create verification passed on 2026-09-06:
  `conan create . -pr:h ohos-aarch64 -pr:b ohos-aarch64 --build=missing`.
- Upstream CTest: `100% tests passed, 0 tests failed out of 502`
  (505 registered, 3 tzdata-snapshot-sensitive entries excluded with
  per-test reasons in reports/test-report.md).
- Conan test_package: `100% tests passed, 0 tests failed out of 1`
  (`PASS: KCalendarCore MemoryCalendar/ICalFormat round-trip OK`).
- Package artifacts: `lib/libKF6CalendarCore.so`, `lib/cmake/KF6CalendarCore/`,
  `include/KCalendarCore/`, `lib/pkgconfig/KF6CalendarCore.pc`.
---

**编译结束**: 2026-09-06 23:00
**最终状态**: built
