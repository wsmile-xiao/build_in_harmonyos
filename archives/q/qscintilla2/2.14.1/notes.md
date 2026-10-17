# qscintilla2 2.14.1 OpenHarmony PC notes

## Scope

This package adapts QScintilla 2.14.1 for OpenHarmony PC. QScintilla is the Qt port of the Scintilla source editing component and is built from the official Riverbank source archive.

## Dependency boundary

QScintilla is a Qt widget library. It consumes `qtbase/6.11.1` as a Conan dependency; qmake and the Qt 6 headers/libs come from the qtbase package folder. No system Qt prefix is required by the recipe.

## Build

Build system: qmake.

Main commands:

```bash
qmake src/qscintilla.pro CONFIG+=release
make -j2
make install INSTALL_ROOT=<package_folder>
```

The qmake project installs into Qt installation paths. The recipe stages with `INSTALL_ROOT` and normalizes the staged `include`, `lib`, and mkspecs/features directories into the Conan package folder.

## Tests

The upstream package ships examples and Python config tests rather than a standalone C++ unit test suite for the library build. Both upstream entries are now covered by the recipe:

1. `example/application.pro` is built against the packaged QScintilla headers and library. The resulting GUI example is started once with `QT_QPA_PLATFORM=offscreen`; a timeout after successful startup is accepted because the upstream example is an interactive application and does not exit by itself.
2. `Python/config-tests/cfgtest_Qsci.cpp` is compiled and run as a C++ configuration probe. The recipe verifies that its generated output contains `2.14.1`.

The `test_package` performs a consumer smoke test:

1. Finds Qt6 Widgets through the `qtbase/6.11.1` Conan dependency's `Qt6_DIR`.
2. Passes the QScintilla package `include` and `lib` directories into CMake as variables and links `qscintilla2_qt6` manually, avoiding `find_package(qscintilla2)` because qtbase uses `cmake_find_mode=none` and has no `qtbase-config.cmake`.
3. Builds and links an executable that includes QScintilla public headers, creates a `QApplication` and `QsciScintilla` instance, and verifies `setText()`/`text()` on the widget.
4. Runs the executable when the host profile can run target binaries. Full editor rendering and input interaction still require manual validation on an OpenHarmony PC display session.

QtPrintSupport is not available in the OHOS `qtbase/6.11.1` package (`FEATURE_printsupport=OFF`). The recipe conditionally drops `QT += printsupport` from `src/qscintilla.pro` and the shipped `qscintilla2.prf` feature files, excludes `qsciprinter.cpp`, and removes the installed `Qsci/qsciprinter.h` when the module is absent. Printing APIs are therefore not part of this OHOS package.

Declared package test pass rate: upstream example and cfgtest are now part of the recipe and are reported from the OpenDesk target log. The `test_package` case passes when target execution is available and uses the qtbase dependency library path. Cross profiles compile and link the consumer executable, then skip runtime execution without using echo/true placeholder commands.

## R40 manual validation marker

R40 manual validation marker: Headless CI covers build, linkage, and widget-object smoke checks only. QScintilla editor rendering and input interaction require an OpenHarmony PC display session. This PR must remain at `partial` status until that manual validation is complete.

## Verification status

The recipe uses the official source archive and SHA-256 listed in `conandata.yml`. Final OpenHarmony CI verification runs through the qtbase dependency graph:

```bash
CI_PACKAGES="archives/q/qscintilla2/2.14.1" zsh ci/conan/build_and_test.sh
```
