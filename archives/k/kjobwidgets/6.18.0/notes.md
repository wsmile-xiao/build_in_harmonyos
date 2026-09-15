# kjobwidgets 6.18.0 notes

## Scope

This recipe upgrades KJobWidgets to the 6.18.0 framework level required by KIO
6.18.0.

## Adaptations

- DBus, X11 integration, Python bindings, and translation catalog generation
  are disabled for the current OHOS baseline.
- `knotifications/6.18.0` is kept as a real dependency because
  `knotificationjobuidelegate.cpp` is part of the library.

## Verification

- Local pre-PR checks on 2026-08-31: `python -m py_compile` for the recipe and
  test recipe passed, and `conan export` succeeded with Conan home inside the
  workspace.
- OHOS real-device `conan create` was not rerun because the test device is
  currently unavailable; PR CI is expected to provide the package build result.
