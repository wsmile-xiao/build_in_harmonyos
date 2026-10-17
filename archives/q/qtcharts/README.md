# Qt Charts

Qt Charts provides Qt 6 chart components such as line, bar, pie and scatter
series.  Version 6.11.1 is built from the official Qt release archive.

## HarmonyOS PC adaptation

The recipe uses CMake and disables upstream examples, benchmarks,
documentation and tests for the package build.  A Conan test package creates a
`QChart` with a `QLineSeries`, creates the default axes and validates the chart
composition through Qt's offscreen platform without requiring a display server.

This adaptation intentionally validates headless/offscreen chart composition.
It does not provide a native HarmonyOS QPA window-system backend, so downstream
applications that require visible Qt windows need a separate QPA integration.

Qt Charts is a Qt module rather than a standalone library.  It requires
`qtbase-gui/6.11.1`, including Qt Core, Gui, Widgets and graphicsview. The CI
image does not ship a system Qt 6 installation, so the dependency is declared
explicitly and Qt's native CMake configurations are used.

The dependency is provided by the separate qtbase-gui PR (#2960) and declared
via the recipe requires; this PR contains only the qtcharts adaptation.
