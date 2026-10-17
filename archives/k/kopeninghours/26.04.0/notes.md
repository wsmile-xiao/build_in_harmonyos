# kopeninghours 26.04.0 notes

## Scope

First HarmonyOS PC adaptation of KDE kopeninghours 26.04.0 — a KDE library
(`libKOpeningHours.so`) that parses and evaluates OpenStreetMap opening
hours expressions (e.g. `Mo-Fr 08:00-12:00`), including variable-time
references (`sunrise`/`sunset`/`dawn-dusk` via kholidays' astronomy code)
and public-holiday references (`PH` via kholidays).

## Upstream form

- CMake + ECM (>= 5.44 REQUIRED, KF6 conventions), Qt6 >= 6.4 (Qt6::Core
  public; Qt6::Qml optional for the QML plugin — not built here)
- Library `KOpeningHours` (SOVERSION 1)
- Parser generated at build time: `src/lib/openinghoursparser.y` (bison) +
  `src/lib/openinghourslexer.l` (flex)
- 7 upstream autotests under `autotests/` (BUILD_TESTING):
  parsertest, jsonldtest, intervaltest, eastertest, evaluatetest,
  iterationtest (links KF6::Holidays), intervalmodeltest
- `ki18n_install(po)` at the top level — runs `msgfmt` (gettext) + a
  Python script at build time to produce .mo catalogs
- Two build-only CLI tools under `tests/` (osm-opening-hours-validate /
  osm-opening-hours-evaluate) — compiled but not installed

## W0 dependency check

| Dependency | Published form used |
|---|---|
| Qt6 Core | qtbase/6.11.1 |
| KF6::I18n (link + ki18n_install macros) | ki18n/6.18.0.1 |
| KF6::Holidays (variable time + iterationtest) | kholidays/6.28.0 |
| ECM | extra-cmake-modules/6.28.0 (tool) |
| bison / flex / m4 (parser gen) | bison/3.8.2, flex/2.6.4.2, m4/1.4.19 (tool) |
| tzdb for named timezones at test time | tzdata/2026.3 (host, kcalendarcore precedent) |

All verified on conan.cnb.cool before starting.

## Adaptation decisions

1. **KF_IGNORE_PLATFORM_CHECK=TRUE** — OHOS is not in the KDE platform
   list; kholidays/kconfig/kdbusaddons precedent.
2. **BUILD_WITH_QT6=ON** — ECM 6.28's `QtVersionOption.cmake` defaults to
   Qt5 when `ECM_GLOBAL_FIND_VERSION` is unset (ECM 6.x does not define it).
3. **ECM_VERSION=6.28.0 (cache var)** — the top-level CMakeLists still has
   the legacy `if (ECM_VERSION VERSION_GREATER_EQUAL 5.91) ... else
   set(QT_MAJOR_VERSION 5)`. ECMConfig.cmake does not define ECM_VERSION,
   so without pinning it the else branch forces Qt5. Both pin together
   select the Qt6 path.
4. **GETTEXT_MSGFMT_EXECUTABLE** set from the gettext package (transitive
   dep of ki18n/6.18.0.1) — `ki18n_install(po)` runs msgfmt at build time;
   OHOS has no system gettext.
5. **BISON_PKGDATADIR + M4** — bison/3.8.2's pkgdatadir is compiled as
   `/share/bison` (built with `--prefix=`); must be redirected into the
   conan package, and M4 pointed at m4/1.4.19 (dawg/libidl precedent).
6. **tzdata/2026.3 + TZDIR/QT_ZONEINFO** — the autotests resolve named
   timezones (evaluatetest sets `TZ=Europe/Berlin`, iterationtest
   `TZ=Pacific/Auckland`, sunrise/sunset astronomy); OHOS ships no
   `/usr/share/zoneinfo` and qtbase is built with `timezone_tzdb` off.
   kcalendarcore precedent. With TZDIR set: evaluatetest 128+4FAIL ->
   132/132, iterationtest sunrise crash -> 29/29.
7. **No python tool_require** — the published python/3.12.9 package's lib
   dir in LD_LIBRARY_PATH shadows the profile-guaranteed system python
   (sys.platform becomes `linux`, breaking sysconfigdata lookup with
   `ModuleNotFoundError: _sysconfigdata__linux_aarch64-linux-ohos`). The
   profile buildenv PATH already guarantees a working python 3.12.9 at
   /storage/Users/currentUser/usr/local/bin (used by ki18n's tsfiles
   step, which is a no-op for this package — no .pmap files).
8. **ECM_MODULE_PATH + conan_cmakedeps_paths.cmake** — set manually
   (kholidays precedent) because CMakeDeps-generated ECMConfig.cmake does
   not propagate ECM_MODULE_PATH and qtbase uses cmake_find_mode=none.
   The manual cmakedeps file replaces the toolchain's find_paths block, so
   kholidays/ki18n lib/cmake dirs are added explicitly as well.
9. **BUILD_TESTING=ON** — the 7 autotests are plain computation tests; they
   run with QT_QPA_PLATFORM=offscreen, isolated XDG/HOME, TZ=UTC and
   TZDIR/QT_ZONEINFO pointing at tzdata's zoneinfo tree.
10. **BUILD_QCH=OFF** — API documentation (needs Qt6Tools) not built.

## Upstream tests

Executed during `conan create` via ctest: **7/7 passed (100%)** —
parsertest (359), jsonldtest (6), intervaltest (6), eastertest (9),
evaluatetest (132), iterationtest (29), intervalmodeltest (6). Also
verified in the exploratory build tree (ctest total 0.74s). The two
`tests/` tools compile but are not installed (upstream does not install
them either).

## Problems hit and fixes

| # | Problem | Root cause | Fix |
|---|---------|-----------|-----|
| 1 | configure picks Qt5 (`FindQt5.cmake` not found) | ECM QtVersionOption defaults to Qt5; legacy `ECM_VERSION` check in top CMakeLists also forces Qt5 | `BUILD_WITH_QT6=ON` + `ECM_VERSION=6.28.0` cache vars |
| 2 | po build fails: `GETTEXT_MSGFMT_EXECUTABLE` missing / msgfmt crashes with `default_destructor: symbol not found` | OHOS has no system gettext; conan gettext msgfmt needs its lib in LD_LIBRARY_PATH | `GETTEXT_MSGFMT_EXECUTABLE` from gettext package + all deps' lib dirs on LD_LIBRARY_PATH during build |
| 3 | `bison: /share/bison/m4sugar/m4sugar.m4: cannot open` | bison 3.8.2 compiled with `--prefix=` | `BISON_PKGDATADIR` + `M4` env in build env |
| 4 | `ModuleNotFoundError: _sysconfigdata__linux_aarch64-linux-ohos` at configure | python/3.12.9 tool_require lib shadows system python's libpython (`sys.platform` -> `linux`) | drop the python tool_require; rely on profile-guaranteed system python |
| 5 | KF6Holidays/KF6I18n not found at configure in conan create | manual conan_cmakedeps_paths.cmake replaces the toolchain find_paths block | add kholidays/ki18n lib/cmake dirs to the manual cmakedeps file |
| 6 | evaluatetest 4 FAIL (`variable time` rows), iterationtest sunrise crash + hang | no tz database on OHOS (Qt `timezone_tzdb` off, no /usr/share/zoneinfo) | tzdata/2026.3 requirement + TZDIR/QT_ZONEINFO in the test env |
| 7 | test_package `fromJsonLd` assertion failed | wrong JSON-LD input shape (single spec object instead of a place with `openingHours` array) | rewrite consumer test to the schema.org `openingHours` array form |

## Consumer test

`test_package/test_kopeninghours.cpp` links `KOpeningHours` and exercises
the public API: parses `Mo-Fr 08:00-12:00`, asserts Monday 09:00 is Open
with correct begin/end, Monday 13:00 is Closed and `nextInterval()` yields
Tuesday 08:00, plus `normalizedExpression()` and schema.org JSON-LD import
via `OpeningHours::fromJsonLd`. Output:

```
kopeninghours consumer probe OK: 'Mo-Fr 08:00-12:00' Monday-09:00=open
Monday-13:00=closed next=Tuesday-08:00 jsonld-ok
```

## Dependency versions

- qtbase/6.11.1, ki18n/6.18.0.1, kholidays/6.28.0, tzdata/2026.3
- extra-cmake-modules/6.28.0, flex/2.6.4.2, bison/3.8.2, m4/1.4.19 (tools)

## Verification

```
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=kopeninghours/*
  -> ctest: 7/7 passed (100% tests passed, 0 tests failed out of 7)
  -> test_package: kopeninghours consumer probe OK
ohc-run.py conan-verify kopeninghours 26.04.0 -> 8/8 gates PASS
```

## Notes

- No source patches needed: every adaptation is build-time configuration or
  environment (patches/ empty).
- The library's DT_NEEDED for libKF6Holidays/libKF6I18n carries absolute
  conan-cache paths (those published KF6 libs have no DT_SONAME) — same
  established pattern as kcolorscheme/kconfigwidgets in this repo.
---

**编译结束**: 2026-09-20 22:07
**最终状态**: published
