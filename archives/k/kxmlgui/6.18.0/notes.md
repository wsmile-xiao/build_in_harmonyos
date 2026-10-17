# kxmlgui 6.18.0 notes

## Scope

This package is part of the Akonadi KF 6.18 baseline. It is based on the
existing remote 6.14.0 recipe and adds a mainline-ready 6.18.0 package
directory without modifying the 6.14.0 branch.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `FORCE_DISABLE_KGLOBALACCEL=ON` avoids the unpublished KF6GlobalAccel
  dependency and disables global shortcut support.
- `USE_DBUS=OFF` avoids Qt6DBus until the shared Qt DBus baseline lands.
- `BUILD_DESIGNERPLUGIN=OFF` avoids Qt6UiPlugin.
- `BUILD_PYTHON_BINDINGS=OFF` avoids Shiboken6/PySide6.
- `KF_SKIP_PO_PROCESSING=ON` avoids translation catalog generation.
- `BUILD_TESTING=ON` runs the upstream CTest autotests during Conan build.
- Qt6PrintSupport is removed from the build by dropping the CMake dependency,
  private link item, and `KShortcutsDialog` Print action; the internal print
  slot is left inert because it is no longer reachable from the dialog.
- `autotests/kxmlgui_unittest.cpp` skips one locale behavior row only when a
  runtime check shows that setting the application-specific language does not
  change `QLocale::system()`.

## Verification

The recipe also supplies consumer-side `OPENSSL_*` cache variables and a minimal `PkgConfig::LibZstd` imported target because `kxmlgui` consumes `kiconthemes -> karchive/6.19.0`, and the reused KArchive package exports those dependencies through its installed CMake config.


Initial local checks:

- Upstream source SHA256 verified:
  `6d5e240c835668419ac036666fa4c99e3479795c6988100763f810ca8835c401`.
- The four OHOS patches were checked against the unpacked 6.18.0 source.

OHOS `conan create` verification passed on 2026-08-19.

- Runner log: `/storage/Users/currentUser/ohos-users/codex-a/kf618-kitemviews-upstream-low-20260819/logs/kxmlgui-r4.log`.
- Full package reference: `kxmlgui/6.18.0#89a3aef1f91f2c588d57b9bf70b9aa65:4bf420217227b899e808a32bf03b9bbe77a2d722#73f6d4c26c84addb2df6d6f819731453`.
- Upstream CTest: 6/6 passed, with the runtime `QLocale::system()` application-language behavior skipped in `kxmlgui_unittest` only when the language update is not observed.
- Conan `test_package`: 1/1 passed.
- Runner results: L0 pass, L1 pass, L5 pass; L2 skip: no bin/ dir; L4 warn: dangerous functions in patches; `RUN_RC=0`.
