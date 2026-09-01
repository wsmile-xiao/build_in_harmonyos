# qtquicktimeline 6.11.1 OpenHarmony PC notes

## Scope

This package adapts the official Qt Quick Timeline 6.11.1 submodule for OpenHarmony PC. It builds the Qt upstream CMake project and packages the QuickTimeline and QuickTimelineBlendTrees libraries and QML plugin metadata.

## Dependency boundary

Qt Quick Timeline requires an existing Qt 6.11.1 installation with Qt Core, Qml, and Quick. It also requires the `cborstreamreader` and `cborstreamwriter` features in Qt Core.

The recipe declares its Qt dependencies with Conan `requirements()` and lets `generate()` point CMake at the resolved Qt package folders. `CMAKE_PREFIX_PATH` is set to the `qtbase/6.11.1` package folder, with explicit `Qt6_DIR` and module `Qt6*_DIR` variables for the declared Qt dependency modules.

The recipe no longer probes system Qt prefixes; `validate()` only rejects host OSes that this HarmonyOS PC adaptation does not support.

## Build

Main CMake options:

```text
BUILD_TESTING=ON
QT_BUILD_EXAMPLES=OFF
QT_BUILD_TESTS=ON
QT_BUILD_TESTS_BY_DEFAULT=ON
CMAKE_PREFIX_PATH=<qtbase package folder (set by generate())>
```

No source patch is required for the 6.11.1 baseline.

## Tests

The upstream tests under `tests/auto` are enabled during the package build. When the target binaries can execute, the recipe runs them with `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software ctest --test-dir <build> --output-on-failure`, covering `tests/auto/qtquicktimeline` and `tests/auto/qtquicktimeline_blendtrees` in the OpenDesk target environment.

The `test_package` performs a consumer smoke test:

1. Resolves `Qt6` and the module components through the `Qt6_DIR`/`Qt6*_DIR` variables generated from the Conan dependencies.
2. Links a small executable against `Qt6::QuickTimeline`.
3. Runs the executable to prove the package can be consumed.
4. Loads `QtQuick.Timeline` and creates a `Timeline` object when target execution is available.

Declared package test pass rate: upstream auto tests are now part of the recipe and must be reported from the OpenDesk target log. The `test_package` case still passes only when target execution is available. Cross profiles compile and link the consumer executable, then skip runtime execution without using echo/true placeholder commands.

## Verification status

The recipe uses the official source archive and SHA-256 listed in `conandata.yml`. Final OpenHarmony CI verification should run after the PR is opened:

```bash
CI_PACKAGES="archives/q/qtquicktimeline/6.11.1.1" zsh ci/conan/build_and_test.sh
```

## R40 manual validation marker

R40 manual validation marker: Headless CI covers build, linkage, and QML type loading only. Qt Quick Timeline animation behavior requires an OpenHarmony PC display session. This PR must remain at `built` status until that manual validation is complete; it must not be promoted to `published` based only on CI smoke tests.
