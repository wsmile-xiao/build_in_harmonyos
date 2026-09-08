# kwindowsystem 6.26.0 notes

## Scope

This package is part of the KF6 chain refresh (task 6329 dependency, layer
3: kwindowsystem after ECM 6.26.0). It updates the published 6.18.0
HarmonyOS PC recipe to KDE Frameworks 6.26.0. The 6.18.0 recipe was used as
the base recipe.

## Upstream changes 6.18.0 -> 6.26.0 (relevant to the OHOS adaptation)

- `cmake_minimum_required` raised from 3.16 to 3.29 (local cmake 4.1.2 and
  the CI toolchain satisfy this).
- Minimum Qt version raised from 6.7.0 to 6.9.0; `qtbase/6.11.1` satisfies
  it. `find_package(Qt6GuiPrivate)` is now guarded by
  `Qt6Gui_VERSION VERSION_GREATER_EQUAL 6.10.0` and `Qt6::GuiPrivate` is in
  the autotest link set - both satisfied by qtbase 6.11.1.
- The X11/Wayland/QML options (`KWINDOWSYSTEM_X11`, `KWINDOWSYSTEM_WAYLAND`,
  `KWINDOWSYSTEM_QML`) are unchanged, so the OHOS baseline keeps all three
  off; WIN32/APPLE/ANDROID/HAIKU auto-disable X11/Wayland upstream, which
  validates the dummy-backend path.
- The `ecm_set_disabled_deprecation_versions` baseline moved
  `QT 6.10.0 -> 6.11.0` (patch hunk context change only).

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `KWINDOWSYSTEM_QML=OFF` disables optional QML bindings.
- `KWINDOWSYSTEM_X11=OFF` and `KWINDOWSYSTEM_WAYLAND=OFF` avoid unavailable
  X11/Wayland stacks on OHOS; the dummy backend keeps the symbols.
- `BUILD_DESIGNERPLUGIN=OFF` avoids Qt6UiPlugin/Qt Designer plugin discovery.
- `BUILD_TESTING=ON` runs the upstream CTest autotests registered by the
  current headless feature set.
- `ECMQmlModule` include and `ecm_install_po_files_as_qm(poqm)` are disabled
  by patch for the minimal OHOS baseline (regenerated for 6.26.0 line
  numbers; semantics identical to the 6.18.0 patch).
- ECM 6.26 `KDEInstallDirs6` runs the qtbase `qtpaths` host tool at
  configure time; the recipe prepends `/system/lib64` (and the SDK llvm lib
  dir) to `LD_LIBRARY_PATH` so the compatible `libc++_shared.so` is found
  (bluez-qt 6.28.0 precedent, also applied in kconfig 6.26.0).

## Verification

- Upstream source SHA256 verified:
  `5f7962b7c986e77c5d25fa4f7d09cd89144b8781e57ebc37fd45eaec1961bb02`
  (https://download.kde.org/stable/frameworks/6.26/kwindowsystem-6.26.0.tar.xz,
  tarball confirmed on the KDE mirror; v6.26.0 tag exists upstream).
- The regenerated patch applies cleanly to the unpacked 6.26.0 source
  (`patch -p1 --dry-run` OK on a pristine copy).
- See manifest.yaml for the `conan create` result and test counts.
---

**编译结束**: 2026-09-05 21:37
**最终状态**: built
