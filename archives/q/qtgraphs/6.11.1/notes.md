# qtgraphs 6.11.1 OpenHarmony PC notes

## Scope

This package adapts the official Qt Graphs 6.11.1 submodule for OpenHarmony PC. It builds the Qt upstream CMake project and packages the Qt Graphs libraries, QML plugin metadata, and CMake package files.

## Dependency boundary

Qt Graphs requires an existing Qt 6.11.1 installation with Qt Core, Gui, Qml, Quick. The recipe declares its Qt dependencies with Conan `requirements()` and lets `generate()` point CMake at the resolved Qt package folders. `CMAKE_PREFIX_PATH` is set to the `qtbase/6.11.1` package folder, with explicit `Qt6_DIR` and module `Qt6*_DIR` variables for the declared Qt dependency modules.

The recipe no longer probes system Qt prefixes; `validate()` only rejects host OSes that this HarmonyOS PC adaptation does not support.

## Build

Main CMake options:

```text
BUILD_TESTING=ON
QT_BUILD_EXAMPLES=OFF
QT_BUILD_TESTS=ON
QT_BUILD_TESTS_BY_DEFAULT=ON
FEATURE_graphs_3d=OFF
CMAKE_PREFIX_PATH=<qtbase package folder (set by generate())>
```

One upstream test data string is adjusted during `source()`: `tests/auto/cpp2dtest/qgaxis-datetime/tst_datetimeaxis.cpp` changes `QString timeZoneString = "Europe/Helsinki";` to `"UTC"` for deterministic timezone-data handling. No other upstream test files are modified.

## Tests

The recipe enables the upstream Qt auto tests with `BUILD_TESTING=ON`, `QT_BUILD_TESTS=ON`, and `QT_BUILD_TESTS_BY_DEFAULT=ON`, then runs `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software ctest --test-dir <build> --output-on-failure --timeout 300` when target binaries can execute. The per-test CTest timeout prevents one hung Qt test from stalling the whole CI batch. OpenDesk target logs are required before claiming the upstream pass rate.

The upstream `tests/auto` CMake wires 45 CTest targets: 17 `cpp2dtest`, 1 `qml2dtest`, 26 `cpptest`, and 1 `qmltest`. The 18 2D targets are enabled and executed in the current OHOS build. The 27 3D targets (`cpptest`/`qmltest`) are gated behind `QT_FEATURE_graphs_3d`, which requires `Qt6Quick3D`; the current adaptation set does not yet include a `qtquick3d` recipe, so the recipe passes `FEATURE_graphs_3d=OFF` to keep that exclusion explicit even if a Qt6Quick3D CMake package is later present in the environment. Two additional `cpp2dtest` theme test directories (`qgtheme-series` and `qgtheme-graph`) are not wired by upstream `tests/auto/cpp2dtest/CMakeLists.txt` and are not counted in the 45 targets. A separate `qtquick3d` adaptation is required before the 3D APIs and tests can be claimed.

`tests/baseline` registers one conditional CTest (`tst_baseline_graphs`) that depends on Qt6Quick3D, qtbase baseline shared, and `QT_FEATURE_process`; it is not included in the 45 `tests/auto` count. `tests/manual` contains 43 directories with 42 manual targets that require an interactive OpenHarmony PC display session and are also not counted in the 45 auto targets.

The `test_package` performs a consumer smoke test:

1. Resolves `Qt6` and the module components through the `Qt6_DIR`/`Qt6*_DIR` variables generated from the Conan dependencies.
2. Links a small executable against `Qt6::Graphs`.
3. Compiles a consumer that includes the module public headers and checks the module version macro.
4. Exercises non-rendering 2D data APIs for bar, line, and scatter series (`QBarSeries`, `QBarSet`, `QLineSeries`, `QScatterSeries`, and `QValueAxis`).
5. Runs the executable under `timeout 120` when the profile can execute target binaries, or verifies that it was built for cross profiles.

Graph rendering depends on the Qt Quick scene graph and must still be manually validated on an OpenHarmony PC display session.

## Verification status

The recipe uses the official source archive and SHA-256 listed in `conandata.yml`. Final OpenHarmony CI verification should run after the PR is opened:

```bash
CI_PACKAGES="archives/q/qtgraphs/6.11.1" zsh ci/conan/build_and_test.sh
```

## R40 manual validation marker

R40 manual validation marker: Headless CI covers build, linkage, and non-rendering smoke checks only. Qt Graphs rendering, QML integration, and EGL/GLES scene graph behavior require an OpenHarmony PC display session. This PR must remain at `built` status until that manual validation is complete; it must not be promoted to `published` based only on CI smoke tests.
