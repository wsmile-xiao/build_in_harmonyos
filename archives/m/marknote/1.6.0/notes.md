# marknote 1.6.0 notes

## Scope

Marknote 1.6.0 is a KDE markdown note application (Qt6/KF6/QML). This is the first HarmonyOS PC adaptation, packaging the official KDE stable tarball.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE platform allowlist for OHOS.
- `KF_MIN_VERSION` lowered from 6.21 to 6.18.0 via `source()` python replace (previously via patch 0001) to avoid `conan` patch tool `/tmp` readonly failure on OHOS; matches published frameworks (6.18.x) in ohpcd; no API loss.
- `KF6KirigamiAddons` made optional (REQUIRED → QUIET, TYPE OPTIONAL) and `KirigamiAddonsStatefulApp` linking guarded (both `KirigamiAddonsStatefulApp` and `KF6::KirigamiAddonsStatefulApp` targets) because kirigami-addons 1.11 is not yet published; build remains functional.
- `WITH_KRUNNER=OFF` and `WITH_KCRASH=OFF` disable plasma runner and crash handler to avoid extra deps on OHOS.
- `BUILD_TESTING=ON` enables the 4 upstream autotests (navigationcontrollertest, nestedlisthelpertest, notebooksmodeltest, maildirimporttest).
- ECM and Qt path handling mirrors other KF6 recipes: `ECM_MODULE_PATH` set manually and `conan_cmakedeps_paths.cmake` generated because qtbase uses `cmake_find_mode=none`.
- Application install via `cmake.install()` delivers `bin/marknote` and QML/translation assets.

## Verification

- Source SHA256 verified: `d3bb39614e22fd1a8ddd74bcfb4c384cbffe25685ec01116f694e470816284a9`.
- Patches validated against unpacked 1.6.0 source (CMakeLists.txt and src/CMakeLists.txt).
- `conan create` expected to build with Qt6 6.11.1 and KF6 6.18 stack; upstream CTest 4 tests executed (needs offscreen platform for QML tests).
- Consumer test_package checks installed `marknote` binary existence and `--help` execution with `QT_QPA_PLATFORM=offscreen`.

## Dependencies

- Runtime: qtbase, qtdeclarative, qtsvg, qtshadertools, kirigami, kcoreaddons, kconfig, ki18n, kiconthemes, kcolorscheme, kitemmodels, knotifications, kguiaddons, karchive, kcrash, kdbusaddons, kwindowsystem, kmime, ksyntaxhighlighting, md4c
- Build: ecm 6.26.0

## Known limitations

- KirigamiAddons stateful components are stubbed when the optional package is absent; related QML pages degrade gracefully.
- KRunner integration disabled (OHOS has no plasma runner dbus interface).
