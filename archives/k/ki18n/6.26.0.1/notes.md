# ki18n 6.26.0.1 notes

## Scope

KDE Frameworks 6 `ki18n` for HarmonyOS PC (aarch64), revision `6.26.0.1`.
This is the front dependency of `kirigami-app 1.0.1`: it ships the **QML module
`org.kde.ki18n`** (`lib/qml/org/kde/ki18n`) in addition to the core libraries
`libKF6I18n.so.6`, `libKF6I18nLocaleData.so.6` and `libKF6I18nQml.so.6`.

Base: published `ki18n/6.26.0` (its recipe sets BUILD_WITH_QML=OFF, so the
published package ships no QML module; this adaptation revision turns QML ON
to ship `org.kde.ki18n`) + the SONAME /
ELF-resign hardening proven on `kitemodels/6.18.0.1` (PR #10520) and
`kirigami/6.26.0` (PR #10787).

## Why 6.26.0.1 instead of fixing 6.18.0.1

The reconnaissance for this task (see `~/runner/ki18n-recon-progress.md`)
established that the `org.kde.ki18n` QML module was only introduced upstream in
KF **6.21** (`src/i18n-qml/CMakeLists.txt`: `ecm_add_qml_module(KF6I18nQml URI
"org.kde.ki18n" VERSION 1.0 GENERATE_PLUGIN_SOURCE)`). 6.18/6.19/6.20 only build
`libKF6I18nQml.so` with no QML module, so no amount of recipe work on 6.18 can
produce it. Hence the 6.26.0.1 re-base.

## Source

- URL: `https://download.kde.org/stable/frameworks/6.26/ki18n-6.26.0.tar.xz`
  (official KDE release; no mirror / re-pack / fork).
- SHA256 verified locally: `484aad486bfafef6c86d8d5b26529258e67c74c96250c1ac212ddf568448c7c0`.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` — OHOS is not in KDE's platform allow-list.
- `BUILD_WITH_QML=ON` — qtdeclarative/6.11.1 (Qt6::Qml) is published and is a
  hard requirement, so `src/i18n-qml` and `src/localedata-qml` are configured,
  built and installed.
- `KF_SKIP_PO_PROCESSING=ON` — skips ki18n's own translation catalog build.
- `BUILD_TESTING=ON` — upstream CTest autotests run inside `build()` (R51).
- `CMAKE_INSTALL_LIBDIR=lib` so the QML tree lands in `lib/qml`.
- `ECM_MODULE_PATH` set manually (the CMakeDeps-generated ECMConfig.cmake does
  not propagate it).
- Qt split-package resolution: qtbase + qtdeclarative are prepended to
  `CMAKE_PREFIX_PATH`/`CMAKE_LIBRARY_PATH`/`CMAKE_INCLUDE_PATH` and to
  `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` through a hand-written
  `conan_cmakedeps_paths.cmake` (both ship relocatable Qt6*Config.cmake with
  `cmake_find_mode=none`).
- `_dependency_runtime_env()` puts the dependency `lib`/`bin`/`libexec` dirs on
  `LD_LIBRARY_PATH`/`PATH` during configure/build/install: the Qt host tools
  (`qmltyperegistrar`, `qmlcachegen`, `moc`, `rcc`) have a RUNPATH pointing only
  at their own package yet still load `libQt6Core.so.6` from qtbase.

### SONAME / DT_NEEDED hardening (kitemodels 6.18.0.1)

OHOS CMake emits no SONAME by default. The QML plugin linked against the sibling
build-tree library then records `../../bin/libKF6I18n.so` in DT_NEEDED, which the
OHOS loader treats as a cwd-relative path and fails to resolve (this is exactly
the defect shipped by ki18n/6.18.0.1). `_configure_ohos_shared_library_rules()`
restores `CMAKE_SHARED_LIBRARY_SONAME_*` / `CMAKE_SHARED_LIBRARY_RUNTIME_*`
through `CMAKE_USER_MAKE_RULES_OVERRIDE_C/CXX`; the plugin now records the bare
`libKF6I18n.so.6`.

### ELF re-signing

CMake rewrites the RUNPATH of installed shared libraries, which invalidates the
OHOS build-time `.codesign` section (the loader then reports "Permission
denied"). `package()` walks the package tree and re-signs every ELF with
`llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign --selfSign 1`
(6 ELF files for this package).

### Gettext patch

`patches/0001-cmake-KF6I18nMacros.cmake.in.patch` changes
`find_package(Gettext REQUIRED)` to `find_package(Gettext QUIET)` in
`KF6I18nMacros.cmake.in`, so consumers that only link `KF6::I18n` are not forced
to locate the Gettext command-line tools. Platform-agnostic (R8), no platform
macros in the patch.

Note: the Conan-generated gettext CMake config declares a non-existent
`asprintf` library and shadows CMake's own `FindGettext` module; the
test_package therefore disables that config via
`CMakeDeps.set_property("gettext", "cmake_find_mode", "none")`.

## Verification

`conan create archives/k/ki18n/6.26.0.1 -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>
--build=missing --user=ohpcd --channel=stable` → PASS (log:
`reports/conan-create.log`; R51/R53 detail: `reports/test-report.md`).

- Upstream CTest: **12/12 executed passed** (`ctest -N`: 16 registered; the 4
  `KF6::I18nLocaleData` tests `kcatalogtest`/`kcountrytest`/
  `kcountrysubdivisiontest`/`ktimezonetest` are excluded — they require the
  optional IsoCodes JSON runtime data, not shipped on OHOS).
- Conan test_package: R34 C++ API + R53 `import org.kde.ki18n` through an
  offscreen `QQmlEngine`, plus qmldir/plugin/.qmltypes and DT_NEEDED assertions.
- conan-verify: G0/G1/G2/G3/G4 PASS; L2/L4/L5 skipped there (package-id parse),
  the authoritative L0/L1/L2/L4/L5 run is W3 (`reports/w3-local-ci.log`).

## Artifacts

```
lib/libKF6I18n.so.6                     (SONAME libKF6I18n.so.6)
lib/libKF6I18nLocaleData.so.6           (SONAME libKF6I18nLocaleData.so.6)
lib/libKF6I18nQml.so.6                  (SONAME libKF6I18nQml.so.6)
lib/plugins/kf6/ktranscript.so          (Qt6Qml translation script plugin)
lib/qml/org/kde/ki18n/qmldir            (module org.kde.ki18n)
lib/qml/org/kde/ki18n/libKF6I18nQmlplugin.so
lib/qml/org/kde/ki18n/KF6I18nQml.qmltypes
lib/qml/org/kde/i18n/localeData/{qmldir,libki18nlocaledataqmlplugin.so,*.qmltypes}
lib/cmake/KF6I18n/KF6I18nConfig.cmake (+ Targets/Macros/…)
include/KF6/KI18n/…, include/KF6/KI18nLocaleData/…
```

No `bin/` directory → R38 `commands.json` is not applicable (pure library +
QML plugin).

## Knowledge gained

- `org.kde.ki18n` was introduced in KF 6.21; 6.18/6.19/6.20 cannot produce it.
- The QML type is the singleton `KI18n` (`LocalizedContext`, `QML_NAMED_ELEMENT`),
  not `KLocalizedContext`; `KLocalization::setupLocalizedContext()` must run
  before QML loads so the singleton can locate the engine root-context object.
- No-SONAME → relative DT_NEEDED; fix with `CMAKE_USER_MAKE_RULES_OVERRIDE`.
- Post-install ELF edit invalidates `.codesign`; re-sign every packaged ELF.
- Conan gettext config shadows `FindGettext` on OHOS (`asprintf`); suppress it
  with `cmake_find_mode=none`.
---

**编译结束**: 2026-09-18 23:00
**最终状态**: built
