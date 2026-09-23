# kauth 6.18.0 notes

## Scope

This recipe upgrades KAuth to the 6.18.0 framework level required by KIO
6.18.0.

## Adaptations

- `KAUTH_BACKEND_NAME=FAKE` and `KAUTH_HELPER_BACKEND_NAME=FAKE` avoid
  Polkit/DBus dependencies in the current OHOS package baseline.
- Translation catalog generation is disabled.

## Verification

- Local pre-PR checks on 2026-08-31: `python -m py_compile` for the recipe and
  test recipe passed, and `conan export` succeeded with Conan home inside the
  workspace.
- OHOS real-device `conan create` was not rerun because the test device is
  currently unavailable; PR CI is expected to provide the package build result.
