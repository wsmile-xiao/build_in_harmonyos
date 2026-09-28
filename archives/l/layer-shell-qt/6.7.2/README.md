# layer-shell-qt

KDE Plasma QtWayland client shell integration (LayerShellQt).

## Description
LayerShellQt implements the wlr-layer-shell Wayland protocol client side for
Qt: it provides the `LayerShellQt::Interface` library
(`libLayerShellQtInterface.so`) and the `layer-shell` Qt Wayland shell
integration plugin so QWindow-based shells (panels, dock, OSD, wallpapers)
can place themselves on a compositor-managed layer.

## Homepage
https://invent.kde.org/plasma/layer-shell-qt

## License
BSD-3-Clause

## Build System
CMake (KDE ECM)

## OHOS Adaptations
- ECM_MODULE_PATH injected manually (CMakeDeps ECMConfig does not propagate it)
- WaylandScanner pinned from qtbase libexec
- `wayland-protocols.pc` regenerated with real package prefix (relocatable fix)
- QtWaylandClient protocol header included before `wayland-client.h` so the
  `wl_fixes` interface (Qt 6.11 protocol addition) is declared despite the
  shared include guard with the wayland 1.22 protocol header
- `libxkbcommon` linked directly (its pkg-config ships a broken prefix)

## Dependencies
qtbase/6.11.1.2, qtwayland/6.11.1, qtdeclarative/6.11.1, wayland/1.22.0,
wayland-protocols/1.36, libxkbcommon/1.6.0, ecm/6.26.0 (tool_require)
