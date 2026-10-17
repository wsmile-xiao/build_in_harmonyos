# KConfig

KConfig is the KDE Frameworks 6 configuration system. It provides
KConfig/KConfigGroup for INI-style persistent configuration,
KDesktopFile for freedesktop.org desktop entry files, KCoreConfigSkeleton /
KConfigSkeleton for typed settings classes, and the kconfig_compiler code
generator (KConfig XT) that turns `.kcfg` XML descriptions into C++ setting
classes.

## OHOS adaptation

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- `KCONFIG_USE_QML=OFF`, `USE_DBUS=OFF` keep the initial Akonadi KF baseline
  minimal (no qtdeclarative / Qt6DBus requirement).
- `ecm_install_po_files_as_qm(poqm)` is patched out: Qt6LinguistTools is not
  part of the qtbase package in this repository.
- ECM 6.26+ `KDEInstallDirs6` executes the qtbase `qtpaths` host tool at
  configure time; the recipe prepends `/system/lib64` to `LD_LIBRARY_PATH`
  so `qtpaths` resolves the compatible `libc++_shared.so` (the sandbox
  default contains an incompatible one under
  `/data/storage/el1/bundle/libs/arm64`).
- From 6.26.0 the upstream `kconfigtest` uses C++20 chrono calendar types
  which the OHOS toolchain (clang 15 / libc++ / cppstd=17) cannot compile;
  the patch skips building that test target on HarmonyOS (it was already on
  the run-time exclusion list).
- Known limitations: five upstream tests are excluded from the runner
  (`kconfigcore-kconfigtest`, `kconfigcore-kdesktopfiletest`,
  `kconfigcore-test_kconf_update`, `kconfiggui-kstandardshortcutwatchertest`,
  `kconfigcompiler-basic-test`).

## Dependencies

- Build: ecm (extra-cmake-modules), CMake >= 3.29 (for 6.26.0), ninja/make
- Runtime/compile: qtbase (Qt6Core, Qt6Xml; Qt6Gui for ConfigGui;
  Qt6CorePrivate only for the upstream autotests)

## References

- Homepage: https://invent.kde.org/frameworks/kconfig
- Sources: https://download.kde.org/stable/frameworks/
