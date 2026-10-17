# KQuickCharts (kquickcharts)

KQuickCharts is a Qt Quick module from KDE Frameworks 6 that provides lightweight,
declarative charting components (bar, line and pie charts) for QML applications,
including live-updating data sources.

## Features

- `org.kde.quickcharts` QML module: `BarChart` / `LineChart` / `PieChart`
- Data sources: `ArraySource`, `MapProxySource`, `HistoryProxySource` (live streaming data)
- `org.kde.quickcharts.controls` module: `AxisLabels`, `GridLines`, `Legend` etc.
- Built with Qt Quick (offscreen/software-render friendly), no C++ public headers — the API is the QML types

## Build System

CMake + KDE ECM (`ecm_add_qml_module`, `qt6_add_shaders`). Requires CMake ≥ 3.29, Qt6 ≥ 6.9
(Qml / Quick / QuickControls2 / ShaderTools), ECM 6.26.0+.

## Dependencies

- qtbase/6.11.1, qtdeclarative/6.11.1, qtshadertools/6.11.1
- ecm/6.26.0 (tool_requires; ecm/6.28.0 not published on ohpcd — see patch 0001)

## OHOS Adaptation Notes

- Pure QML module: no public C++ headers; consumers use `import org.kde.quickcharts`.
- `qt_add_qml_module` (Qt 6.11) drops VERSION/SOVERSION on the backing library, so the `.so`
  has no ELF SONAME and plugins record a CWD-relative `DT_NEEDED`. Patch 0001 forces
  `-Wl,-soname,libQuickCharts.so.1` and the recipe creates versioned symlinks so runtime
  resolution works via `LD_LIBRARY_PATH` (not the CWD).
- ECM variables (`ECM_GLOBAL_FIND_VERSION` / `ECM_MODULE_DIR` / `ECM_MODULE_PATH`) are not
  provided by CMakeDeps and must be set manually in the toolchain.
- Upstream autotests (4 C++ + 3 QML) run under `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software`; 7/7 pass.
- Difference vs Linux: signing of the packaged `.so` files for OHOS ELF.

## Known Issues

- Downstream `find_package(KF6QuickCharts)` consumers need ECM available (it is a tool_require
  and does not propagate automatically); the primary consumption path is the QML import.
