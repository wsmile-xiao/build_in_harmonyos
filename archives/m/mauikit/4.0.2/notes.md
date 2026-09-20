# mauikit 4.0.2 notes (HarmonyOS PC port)

## Scope

Provides the `MauiKit4` CMake target (the installed export has no NAMESPACE;
the `MauiKit4::Controls` alias exists only in the build tree): a core shared
library (SOVERSION 4) and the QML payload for the Maui ecosystem:

- `org.mauikit.controls` QML module (plugin `libMauiKit4plugin`, sources in
  `src/mauikit.cpp`, NO_GENERATE_PLUGIN_SOURCE),
- `org.mauikit.style` Quick Controls style (plugin `libMauiStyleplugin`,
  generated plugin source) bundled with `BUNDLE_MAUI_STYLE`,
- installed C++ headers under `include/MauiKit4/Core`.

FileBrowsing is not part of this source tree (upstream split it into the
separate mauikit-filebrowsing repository, package MauiKitFileBrowsing4).

## Upstream source

- URL: https://download.kde.org/stable/maui/mauikit/4.0.2/mauikit-4.0.2.tar.xz
- SHA256: `054dc0e15242ffa6bb9b8b25515cebfc9a02347b679f3907dcb80673ca93dd40`
- upstream tag `v4.0.2` = `9d336194a207ffd91a6cd32842c53282a792bef2`

## License note

The recipe declares `LGPL-3.0-or-later` because the shipped `LICENSES/`
directory contains `LGPL-3.0.txt` and the library/QML sources carry
LGPL-3.0-or-later headers. The root `CMakeLists.txt` SPDX header says
`GPL-3.0-or-later`, which covers the CMake build scripts; the difference is
upstream's own inconsistency and is recorded here instead of patching
license files.

## Platform facts (probed on the OHOS device)

With `os=OHOS` the OHOS conan profile maps to `CMAKE_SYSTEM_NAME=HarmonyOS`,
where CMake `UNIX`, `ANDROID`, `APPLE` and `LINUX` are all `false`. As a
result the upstream `find_package(XCB)`, `KF6::WindowSystem`, and the
`platforms/linux|android|windows|macos` **CMake source lists** are skipped
untouched.

Important distinction: the OHOS clang toolchain (target
`aarch64-unknown-linux-ohos`) still defines `__linux__` and `__OHOS__`, so
**Qt's `Q_OS_LINUX` code branches are live on HarmonyOS** even though the
CMake variable is false. Two consequences are patched:

- `src/platforms/platform.cpp` unconditionally fell into its `#else`
  (desktop linux) branch, including the never-compiled `mauilinux.h` with
  the XCB-based `MAUIKDE` backend. Patch 0003 adds an `__OHOS__` branch with
  a minimal in-file `AbstractPlatform` backend (desktop input defaults,
  no-op share, darkModeEnabled=false).
- `FMH::isLinux()`/`Handy::isLinux()` legitimately return `true` on HarmonyOS;
  the test_package asserts this instead of a false negative.

`mauikit.cpp` also registers `private/linux/WindowControls.qml` under
`Q_OS_LINUX`, but that QML file is not added to the module when CMake
`LINUX` is false. Registration is lazy, so the module still loads; an
explicit `WindowControls` instantiation would fail, which the
`enableCSD=false` default avoids (no CSD window controls requested).

## Adaptations

- **MauiMan removed (run decision B, `progress.mauiman_decision`)**: upstream
  hard-requires `MauiMan4 4.0.2`. On OHOS the mauiman server/daemon is never
  built (it is gated on UNIX), so the library would only ever read defaults.
  Patch 0001 removes the `find_package(MauiMan4)`, the link line and all
  code touchpoints in `csdcontrols`, `handy`, `style` and `moduleinfo`
  (including the unused `aboutMauiMan()` descriptor). The patched code falls
  back to the in-class defaults: `enableCSD=false`, window controls theme
  `Nitrux`, `formFactor=Desktop`, `singleClick=true`, `isTouch=false`,
  `styleType=Light`, `accentColor=#26c6da`, `radiusV=4`, `iconSize=22`,
  `hasKeyboard/hasMouse=true` and
  `contentMargins/defaultPadding/defaultSpacing=4` (the latter three got new
  initializers in `style.h` because upstream left them uninitialized and
  only ever assigned them from MauiMan). `QT_QUICK_CONTROLS_MOBILE` remains
  honored as the mobile-mode override.
- **OHOS platform backend** (patch 0003): see "Platform facts" above.
- **QtMultimedia QML gap**: the published `qtmultimedia/6.11.1` package
  ships C++ libraries only - no QtMultimedia QML import tree (the same gap
  already documented for kirigami-addons/1.13.0). Upstream declares
  `"QtMultimedia"` in `ecm_add_qml_module(DEPENDENCIES ...)`, which lands in
  the installed `qmldir` as a module dependency and would make the whole
  `org.mauikit.controls` module unloadable. Patch 0002 drops that entry and
  turns the `ToastArea.qml` notification `SoundEffect`s into no-op
  `QtObject`s with the same `play()` API. The C++ dependency stays: the root
  CMakeLists still finds Qt6 Multimedia and the core library still links
  `Qt6::Multimedia`.
- `ki18n_install(po)` is kept; the recipe resolves `GETTEXT_MSGFMT_EXECUTABLE`
  up front (PATH first, then the device gettext location) so the .po
  processing does not depend on the worker shell PATH.
- `BUILD_DEMO=OFF` (upstream default) and `BUNDLE_LUV_ICONS=OFF` pinned - the
  latter would `git clone` the Lüv icon theme at configure time on other
  platform branches.
- OHOS shared-library rules (soname/-rpath override flags), `$ORIGIN` build
  RPATH, `--disable-new-dtags`, sibling DT_NEEDED normalization
  (`../bin/libMauiKit4*.so` -> bare sonames, including the two QML plugins)
  and ELF self-signing follow the established kirigami recipe pattern.
- **SONAME-less published dependencies**: the published kcoreaddons,
  ki18n, knotifications and qtmultimedia packages ship
  `libKF6*.so`/`libQt6Multimedia.so` without a `DT_SONAME`, so the linker
  bakes their absolute package paths into `DT_NEEDED` (found in CI
  attempt 1; the same published-package gap the kio test_package
  bridges). The recipe normalization rewrites those entries to bare
  basenames, which resolve through the consumer
  `LD_LIBRARY_PATH`/`DT_RPATH` closure. The test_package asserts the
  packaged libraries carry bare sonames only, while the test binary's
  own absolute entries must resolve to existing files.

## Upstream tests

`NO_UPSTREAM_TESTS`: the 4.0.2 tarball contains no `autotests/` or `tests/`
directory and no `BUILD_TESTING` switch in any CMakeLists (root, `src/`,
`src/style.6/`). There is no upstream ctest to wire into `build()`.
Verification is the OHOS-specific `test_package`, which must execute for real
during `conan create` (CI gate L1a) and covers:

- `meta_objects`: exported C++ API (`MauiKitCore::versionString()`, Handy
  meta object properties/enum),
- `ohos_defaults`: the patched MauiMan fallback defaults plus the assertion
  that HarmonyOS matches none of the upstream platform guards and that the
  `QT_QUICK_CONTROLS_MOBILE` override still works,
- `qml_module`: the `org.mauikit.controls` plugin loads and a real control
  instantiates under the offscreen QPA in an isolated HOME/XDG sandbox,
- DT_NEEDED soname hygiene of the test binary and the packaged libraries.
