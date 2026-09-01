# neovim-qt 0.2.19 OpenHarmony PC notes

## Scope

This package adapts neovim-qt 0.2.19, a Qt GUI frontend for Neovim, for OpenHarmony PC. It builds and installs the `nvim-qt` executable and related runtime assets.

## Dependency boundary

neovim-qt consumes `qtbase/6.11.1` and `qtsvg/6.11.1` as Conan dependencies for Core, Network, Widgets, Test, and SvgWidgets. It also expects a Neovim executable at runtime. No system Qt prefix is required.

## Build

Main CMake options:

```text
WITH_QT=Qt6
ENABLE_TESTS=ON
USE_SYSTEM_MSGPACK=OFF
CMAKE_PREFIX_PATH=<qtbase package_folder>;<qtsvg package_folder>
Qt6_DIR=<qtbase package_folder>/lib/cmake/Qt6
Qt6Svg_DIR=<qtsvg package_folder>/lib/cmake/Qt6Svg
Qt6SvgWidgets_DIR=<qtsvg package_folder>/lib/cmake/Qt6SvgWidgets
```

Source patches for OHOS/Qt6 adaptation are applied by `conanfile.py`; see `manifest.yaml` `patches_applied`.

## Tests

The upstream repository contains Qt Test based tests under `test/` and shell widget tests under `src/gui/shellwidget/test/`. The recipe configures `ENABLE_TESTS=ON` and runs `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software ctest --test-dir <build> --output-on-failure` when target binaries can execute. CTest registers 20 targets; the recipe excludes tst_shell for headless runs, leaving 19 enabled. An older OpenDesk round6 log reports `17/20` passing; this is a historical result, and the current head is pending OpenDesk revalidation. The 3 round6 failures were `libQt6Svg` relative loader path errors that the round8 qtbase/qtsvg dependency mode addresses.

The `test_package` now performs the six declared non-rendering package assertions recorded in `test_package/MANIFEST.yml` (executable packaging, desktop launcher metadata, icon resources, and `--version` execution when target binaries can execute). This is still a headless package validation; GUI window creation, rendering, and input handling must be manually confirmed on an OpenHarmony PC display session before claiming full GUI adaptation.

## Verification command

```bash
CI_PACKAGES="archives/n/neovim-qt/0.2.19.1" zsh ci/conan/build_and_test.sh
```

## R40 manual validation marker

R40 manual validation marker: Headless CI covers build, linkage, and non-rendering smoke checks only. neovim-qt GUI window creation, rendering, and keyboard/mouse input require an OpenHarmony PC display session. This PR must remain at `built` status until that manual validation is complete; it must not be promoted to `published` based only on CI smoke tests.
