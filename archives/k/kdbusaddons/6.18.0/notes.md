# kdbusaddons 6.18.0 notes

## Scope

This package provides `KF6::DBusAddons`, needed by later Akonadi calendar and
identity-management libraries.

## Adaptations

- The recipe uses `qtbase-sql-dbus/6.11.1` because `KF6::DBusAddons` requires
  `Qt6::DBus`.
- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `KF_SKIP_PO_PROCESSING=ON` skips translated catalog generation for this
  baseline library package.
- `WITH_X11=OFF` avoids the optional Qt X11 private header path; the current
  OHOS Qt package does not provide that X11 integration and the Akonadi
  calendar chain only needs the DBus library target.
- `BUILD_QCH=OFF` skips optional API documentation generation.
- `BUILD_TESTING=ON` keeps upstream CTest enabled during package creation.

## Verification

Initial checks:

- Upstream source SHA256:
  `dce95cd146e18b400c4df31ea8c9bbba8f919e329a52dc1a19635184ac85e49a`.
- Conan `test_package` finds `KF6DBusAddons`, links with `Qt6::DBus`, and
  verifies a `KDBusService` runtime smoke without requiring a live session bus.

OHOS `conan create` verification passed:

- Package build/install completed and exported `KF6DBusAddons`.
- Upstream CTest: one test was registered, `kdbusservicetest`, but it is not
  executable in the current OHOS package profile because it requires a live
  DBus session bus and neither `dbus-daemon` nor `dbus-launch` is available.
- Conan `test_package`: 1/1 passed.
- Direct consumer run:
  `PASS: KDBusAddons meta-object = KDBusService`,
  `PASS: KDBusAddons session bus connected = 0`, and
  `PASS: KDBusAddons service registered = 0`.
- Full reference:
  `kdbusaddons/6.18.0#5ecacb20d378e81239ac562ce8702d04:fe643a6a365d349533fe6eecb9772405e9423933#d9889f2164a2dc57c65dba8ddde8031f`.

## Upstream Tests Not Run

`kdbusservicetest` is not run in the final recipe. A full CTest attempt was
made and failed before test assertions because no DBus session bus was
available. The current OHOS package profile provides neither `dbus-daemon` nor
`dbus-launch`, so there is no supported way to start the session bus the test
requires. The final recipe still builds the test target and records it with
`ctest -N`, while the Conan `test_package` verifies installed library
consumption without requiring a live bus.
