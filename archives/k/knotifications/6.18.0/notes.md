# knotifications 6.18.0 notes

## Scope

This recipe upgrades KNotifications to the 6.18.0 framework level required by
KJobWidgets 6.18.0.

## Adaptations

- DBus and Canberra notification backends are disabled for the current OHOS
  baseline.
- Python bindings and translation catalog generation are disabled.

## Verification

- Local pre-PR checks on 2026-08-31: `python -m py_compile` for the recipe and
  test recipe passed, and `conan export` succeeded with Conan home inside the
  workspace.
- OHOS real-device `conan create` was not rerun because the test device is
  currently unavailable; PR CI is expected to provide the package build result.
