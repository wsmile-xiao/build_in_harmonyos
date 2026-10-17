# KCalendarCore

KCalendarCore is a KDE Frameworks 6 library for accessing calendars and
scheduling information: events, todos, journals, free/busy data and their
recurrence rules. It reads/writes the ICal format (RFC 2445) through
libical and also understands vCal and xCal. Ships `libKF6CalendarCore.so`.

## OHOS adaptation

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- `USE_QML=OFF`: the QML plugin needs Qt6Qml, which is not part of the
  qtbase package in this repository.
- `BUILD_PYTHON_BINDINGS=OFF`: Shiboken6/PySide6 are not available on
  OHOS; upstream only auto-disables them on ANDROID/APPLE/WIN32/HAIKU and
  static builds.
- No po/qm handling needed: the 6.26.0 tarball ships no translations
  directory and no `ecm_install_po_files_as_qm` call.
- The upstream CTest suite (505 registered entries: 44 unit tests +
  461 data-driven) runs during the Conan build with `BUILD_TESTING=ON`
  (502 executed, 3 tzdata-snapshot-sensitive entries excluded with
  documented reasons); the data-driven entries execute through
  `autotests/runsingletestcase.pl` (`perl/5.42.2` tool_requires + `diff`).
- ECM 6.26+ `KDEInstallDirs6` executes the qtbase `qtpaths` host tool at
  configure time; the recipe prepends `/system/lib64` to `LD_LIBRARY_PATH`
  so `qtpaths` resolves the compatible `libc++_shared.so` (the sandbox
  default contains an incompatible one under
  `/data/storage/el1/bundle/libs/arm64`).
- Tests touching named timezones resolve through libical's builtin tzdata
  (`share/libical/zoneinfo`); the test run pins `TZ=UTC` so the local zone
  database is not needed.

## Dependencies

- Build: ecm (extra-cmake-modules), perl (for the data-driven test runner), CMake >= 3.29, ninja/make
- Runtime/compile: qtbase (Qt6Core/Qt6Gui), libical >= 3.0

## References

- Homepage: https://invent.kde.org/frameworks/kcalendarcore
- Sources: https://download.kde.org/stable/frameworks/6.26/kcalendarcore-6.26.0.tar.xz
