# kirigami 6.18.0 notes

## Scope

This package provides the `KF6::Kirigami` CMake target required by
`purpose/6.18.0` in the Akonadi Calendar dependency chain.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` enables KDE Frameworks builds on OHOS.
- `BUILD_TESTING=OFF` and `BUILD_EXAMPLES=OFF` keep the first package focused
  on the library and QML module payload.
- `DESKTOP_ENABLED=OFF` skips the desktop style plugin path.
- `USE_DBUS=OFF` avoids DBus-specific Kirigami platform code for the initial
  dependency package.
- CMake prefix/module/include paths are populated from Conan dependencies so
  Qt and ECM config packages resolve in the OHOS CI environment.

## Verification

- Source archive SHA256 was verified against
  `e0574bf5f530a7cd98e0342498681f4374beff108e74262063b105e1c977f866`.
- Local `python -m py_compile` and `conan export` are expected before PR
  submission.
- OHOS CI is used for build and `test_package` verification because the real
  device is temporarily unreachable.

## Upstream Tests Not Run

- Upstream Kirigami 6.18.0 includes QML/Quick tests. They are disabled in this
  initial package because the current chain only needs the installed
  `KF6::Kirigami` consumer target and the device-backed OHOS test runner is not
  reachable locally.
