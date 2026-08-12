# adwaita-qt 1.4.2 adaptation notes

## Source And Version

- Upstream: https://github.com/FedoraQt/adwaita-qt
- Release/tag: 1.4.2
- Archive: https://github.com/FedoraQt/adwaita-qt/archive/refs/tags/1.4.2.tar.gz
- SHA-256: cd5fd71c46271d70c08ad44562e57c34e787d6a8650071db115910999a335ba8

## Dependency Gate

- `qtbase/6.11.1` resolves from `ohpcd` for OHOS/arm64 with `--build=never`.
- A fresh component-level probe found no `Qt6DBusConfig.cmake` or Qt6DBus library in the published `qtbase/6.11.1` package.
- Source audit shows `QDBusConnection` is only an unused include in `src/style/adwaitastyle.cpp`; no QDBus symbols are referenced elsewhere. The patch removes the unused hard dependency instead of introducing an unavailable DBus provider.

## Build Choices

- Build upstream in Qt6 mode with `USE_QT6=ON`.
- Keep `BUILD_EXAMPLE=OFF`; the demo is an interactive showcase, not an upstream test suite.
- Install the style plugin under `lib/qt6/plugins/styles` inside this package and export `QT_PLUGIN_PATH` through Conan `runenv_info`.
- On OHOS, provide the missing CMake SONAME/RPATH linker flags through the Conan toolchain so in-tree library consumers record basename `DT_NEEDED` entries instead of build-tree relative paths.
- On OHOS, set `ADWAITAQT_VERSIONED_SHARED_LIBS=OFF` so upstream's shared targets keep real unversioned `.so` files and avoid HMDFS symlink creation. The CMake option defaults to `ON` for upstream-compatible behavior on other platforms.

## Test Inventory

- Upstream tests: 0/0. The release has no `tests` directory, no `enable_testing()`, no `add_test()`, and no documented automated test command.
- Added consumer test: 1/1. It finds the native AdwaitaQt6 CMake package, links the library target, starts Qt with the offscreen QPA backend, discovers the packaged style plugin through `QT_PLUGIN_PATH`, creates the Adwaita style, and checks non-visual palette/metric behavior.

## Findings

- ✅ `qtbase/6.11.1` publishes Qt6 Core/Gui/Widgets but not Qt6 DBus; the adwaita-qt 1.4.2 DBus usage was an unused include and CMake link only, so removing the hard dependency is a narrow source-compatible fix.
- ✅ Qt style plugins must be installed under this package's own `lib/qt6/plugins` tree and exported through Conan `runenv_info` as `QT_PLUGIN_PATH` so consumers can discover the style without system plugin paths.
- ✅ CMake shared libraries on HarmonyOS need explicit SONAME/RPATH linker variables; when upstream also sets `VERSION`/`SOVERSION`, HMDFS symlink creation can fail, so the recipe keeps basename SONAMEs while disabling versioned shared-library filenames for this target.

## Invalid W3 Attempt

- Report: `reports/invalid-w3-20260808-2133.md`.
- Device: `10.62.148.108:2222`.
- Run root: `/storage/Users/currentUser/openharmony-w3/adwaita-qt-1.4.2-slot2-20260808-205218`.
- Result: invalid and failed. It had no atomically FREE shared-lock/lease preflight; readback showed ScaLAPACK/MPICH r36 owned `/storage/Users/currentUser/ohos-users/.device-build.lock` and still had live runner/build/test processes.
- Technical failure captured before the run stopped: CMake tried to create versioned shared-library symlinks such as `libadwaitaqt6priv.so.1`, which failed with `Permission denied` on the target filesystem after SONAME linker flags were enabled.

This attempt is evidence for the symlink/SONAME fix only. It is not valid W3
pass evidence. A later W3 must run from a fresh frozen input on one atomically
FREE authorized device and verify package ELF metadata plus the consumer test.

## Valid W3

- Report: `reports/valid-w3-20260810-807f-215229.md`.
- Device: `10.62.215.229:2222`.
- Run root: `/storage/Users/currentUser/codex-tasks/adwaita-qt-1.4.2-task837-807f-20260810-234006`.
- Snapshot: `807fa2c350480cb15271d1891f23b2b991916fd5`.
- Frozen W3 input tree: `65f48cc47db8e3cb49a78aa2d555abf3a8349460`.
- Candidate input SHA-256: `e7aa22e1846170274dc08688679eed5864f63be11d5468bf8163c70821017850`.
- Launch bundle SHA-256: `fc4bc1ca24216cbc6209934fdb5b9cc7fa0022ccb9686168355f067c1460e9fb`.
- Result: W3 PASS, exit 0, upstream tests 0/0, added consumer tests 1/1.
- Release readback: runner PID 24479 absent, root-bound process count 0, task lock absent, task lease absent.
- Local evidence bundle: `E:\HarmonyPC\tmp\adwaita-qt-w3-807f-215229-20260810-234006\remote-terminal-evidence-pull1.tgz`.
- Evidence bundle SHA-256: `6a909a5fa8457d0fcf95cec44ab9b6eb8b18055f101b07ce2e2b196cdb02de2c`.

The fixed W3 candidate has W0 dependency resolution, W2 structure and patch
replay, one complete W3 PASS on the authorized HarmonyOS/aarch64 device, and W5
metadata closed. Final independent W4 is maintained outside these immutable
W3 result surfaces and must bind the final commit directly. The preserved f972
pass and earlier exit 141/31/invalid attempts are history only and are not reused
as 807f pass evidence.
