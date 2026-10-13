# kpackage5

KDE Frameworks 5 `kpackage` (Qt5), packaged for OpenHarmony PC.

| Item | Value |
|---|---|
| Upstream | https://invent.kde.org/frameworks/kpackage |
| Version | 5.116.0 (final KF5 release) |
| Source | https://download.kde.org/stable/frameworks/5.116/kpackage-5.116.0.tar.xz |
| SHA-256 | `5705b185c72b09f19215fa659fc628dc74529bb7d3f649d1fc953ae5a7ebf1be` |
| Build system | CMake + extra-cmake-modules, tests under CTest |
| Language | C++ (Qt5) |
| Status | built - 11/11 upstream CTest pass on Harmony PC, no exclusion |

This is the KF5/Qt5 module. It is not the same package as `kpackage` 6.x, which
is the Qt6-based KF6 module already published in this repository.

## Status

Device-verified on the Harmony PC: the package builds, packages, and
**all 11 upstream CTest entries run and all 11 pass**, plus a passing consumer
test. No test is excluded.

`KF5Archive >= 5.116.0` (`CMakeLists.txt:47`) is provided by
`karchive5/5.116.0`, delivered as its own device-verified adaptation.

Four tests previously died at load time with
`Error loading shared library libKF5CoreAddons.so.5: Permission denied`; the
cause was an invalid `.codesign` section in the published `kcoreaddons5`
package, which HarmonyOS reports as a permission error. See `5.116.0/notes.md`
for the probe output and the re-signing A/B that proves it.

## Dependencies

- `qt5-qtbase/5.15.2.2` (Qt5 Core + Qt5 DBus; 5.15.2 is -no-dbus and unusable)
- `karchive5/5.116.0` (missing)
- `kcoreaddons5/5.116.0`
- `ki18n5/5.116.0`
- `ecm/6.26.0` (build tool)
