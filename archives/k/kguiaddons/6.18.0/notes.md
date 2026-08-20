# kguiaddons 6.18.0 notes

## Scope

This package is part of the Akonadi KF 6.18 baseline. It updates the
published 6.14.0 HarmonyOS PC recipe to KDE Frameworks 6.18.0 while keeping
the `KF6::GuiAddons` library surface available to downstream packages.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `WITH_WAYLAND=OFF` and `WITH_X11=OFF` avoid desktop-session integrations and
  unavailable Qt/Wayland/X11 dependencies.
- `USE_DBUS=OFF` avoids Qt6DBus until the shared Qt DBus baseline lands.
- `BUILD_PYTHON_BINDINGS=OFF` avoids Shiboken6/PySide6.
- `BUILD_GEO_SCHEME_HANDLER=OFF` skips the optional geo URI desktop handler.
- `BUILD_TESTING=ON` runs the upstream CTest autotests during Conan build.
- CMake configure/build prepends the OHOS SDK `native/llvm/lib` directory to
  `LD_LIBRARY_PATH` so SDK `lld` can load its matching `libxml2.so.16` on CI
  workers that do not export that path globally.

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `2e2b872802d1b27b185512ffa9895906e7aa3438cbf137846ccff8216bbec466`.
- No source patch is required for the 6.18.0 minimal OHOS baseline.

OHOS `conan create` verification passed on 2026-08-19.

- Runner log: `/storage/Users/currentUser/ohos-users/codex-a/kf618-kitemviews-upstream-low-20260819/logs/kguiaddons-r1.log`.
- Full package reference: `kguiaddons/6.18.0#57dbb0826405f7a2880deba297005f08:57ffd8c720a5bfee7e8827990cd6550a49181c1b#150bc5bbbb081af0371e2b312fbdcef6`.
- Upstream CTest: 8/8 passed.
- Conan `test_package`: 1/1 passed.
- Runner results: L0 pass, L1 pass, L4 pass, L5 pass; L2 skip: no bin/ dir;
  `RUN_RC=0`.
