# qtbase-gui

`qtbase-gui` packages the Qt 6 foundation needed by graphical Qt modules on
HarmonyOS PC.

| Version | Status | Modules |
|---------|--------|---------|
| 6.11.1 | pending | Core, Network, Gui, Widgets, Xml |

The package is intentionally separate from the Core-only `qtbase` Conan
package. It provides Qt's native `Qt6Config.cmake` files and real
`Qt6::Core`, `Qt6::Network`, `Qt6::Gui`, and `Qt6::Widgets` targets for
downstream modules such as Qthttpserver and Qtcharts.
