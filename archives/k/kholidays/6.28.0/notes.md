# kholidays 6.28.0 notes

## Scope

First HarmonyOS PC adaptation of KDE Frameworks kholidays 6.28.0. Motivated
by task #12875 (knighttime 6.7.2): knighttime's core API
(`KDarkLightSchedule::forecast`) computes the dark-light schedule from
`KHolidays::SunEvents`, so kholidays must be built and published first
(R36 dependency topological order). Task #7826 claimed for this purpose.

## Upstream form

- CMake + ECM (>= 6.28.0 REQUIRED), Qt6 >= 6.8 (Qt6::Core public, Qt6::Qml
  for the declarative plugin)
- Library `KF6Holidays` (VERSION 6.28.0, SOVERSION 0)
- Parser generated at build time: `parsers/plan2/holidayparserplan.ypp`
  (bison) + `holidayscannerplan.lpp` (flex)
- 7 upstream autotests under `autotests/` (BUILD_TESTING):
  testlunar, testseasons, testsunriseset, testzodiac, testholidayregion,
  testsunevents, testcategories
- `ecm_install_po_files_as_qm(poqm)` at the top level (needs
  Qt6LinguistTools at build time)

## W0 dependency check

| Dependency | Published form used |
|---|---|
| Qt6 Core | qtbase/6.11.1 (r04 consumption gate) |
| Qt6 Qml (declarative plugin) | qtdeclarative/6.11.1 |
| ECM >= 6.28.0 | extra-cmake-modules/6.29.0 (tool) |
| Qt6LinguistTools (poqm) | qt6linguisttools/6.11.1 (tool) |
| bison / flex / m4 (parser gen) | bison/3.8.2, flex/2.6.4, m4/1.4.19 (tool) |

All verified on conan.cnb.cool before starting (PF4 probes).

## Adaptation decisions

1. **KF_IGNORE_PLATFORM_CHECK=TRUE** — OHOS is not in the KDE platform
   list; same as kconfig 6.26.0 / kdbusaddons 6.29.0 precedents.
2. **Parser generation in-recipe** — bison/flex/m4 declared as
   tool_requires so the CI clean environment regenerates
   holidayparserplan.cpp / holidayscannerplan.cpp (the release tarball
   does not ship pre-generated parser sources). acpica-unix precedent.
3. **poqm kept enabled** — qt6linguisttools/6.11.1 is published, so
   `ecm_install_po_files_as_qm(poqm)` runs (kdbusaddons precedent). No
   source patch needed.
4. **ECMGenerateQDoc gracefully degrades** — Qt6Tools not published;
   the ECM module messages "not generating API documentation" and returns
   without failing the configure. No patch needed.
5. **ECM_MODULE_PATH + conan_cmakedeps_paths.cmake** — set manually
   (kdbusaddons/kconfig precedent) because CMakeDeps-generated
   ECMConfig.cmake does not propagate ECM_MODULE_PATH and qtbase uses
   cmake_find_mode=none.
6. **BUILD_TESTING=ON** — the 7 autotests are plain computation tests
   (no display, no D-Bus); they run with QT_QPA_PLATFORM=offscreen, an
   isolated XDG/HOME tree and TZ=UTC.

## Upstream tests

Executed during `conan create` via ctest: **7/7 passed (100%)** — testlunar,
testseasons, testsunriseset, testzodiac, testholidayregion, testsunevents,
testcategories (verified on the build tree after the run; total time 0.43s).

## Problems hit and fixes

| # | Problem | Root cause | Fix |
|---|---------|-----------|-----|
| 1 | Qt6Qml component not found at configure | qtbase's Qt6Config.cmake resolves components relative to its own prefix only | `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` set to the qtdeclarative package root (also added to conan_cmakedeps_paths.cmake with FORCE) |
| 2 | Qt6LinguistTools component not found (ECMPoQmTools REQUIRED) | same prefix-resolution issue for the split qt6linguisttools package | qt6linguisttools package root appended to QT_ADDITIONAL_PACKAGES_PREFIX_PATH |
| 3 | holidayregion.cpp: `invalid argument type 'void' to unary expression` | profile cppstd=17 compiled C++20 sources | `tc.blocks.remove("cppstd")` + CMAKE_CXX_STANDARD=20 (baloo 6.28.0 precedent) |
| 4 | holidayregion.cpp: `no member named 'none_of' in namespace 'std::ranges'` | OHOS SDK libc++ (clang 15) does not ship C++20 ranges algorithm overloads | portability patch 0001: `std::ranges::none_of(r, p)` -> `std::none_of(r.cbegin(), r.cend(), p)` |
| 5 | test_package first draft used deprecated utcSunrise/utcSunset returning QTime (API changed in 6.15: QDateTime -> QTime) | consumer test written against the pre-6.15 API surface | rewritten around SunEvents + isPolarDay/isPolarNight (12 assertions) |

## Consumer test

`test_package/test_kholidays.cpp` links `KF6::Holidays` and exercises the
public astronomy API with astronomically verifiable assertions. Output on
this machine:

```
kholidays consumer probe OK: Beijing solstice sunrise 2025-06-21T04:46:03
sunset 2025-06-21T19:46:18 (day 15.0042h)
```

(Real-world Beijing solstice values: sunrise ~04:46, sunset ~19:46 —
the computation matches.)
