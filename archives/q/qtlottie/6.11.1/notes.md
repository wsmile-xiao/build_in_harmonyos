# qtlottie 6.11.1 OpenHarmony PC notes

## Scope

This package adapts the official Qt Lottie 6.11.1 submodule for OpenHarmony PC. It builds the Qt module with the Qt upstream CMake project and installs the generated libraries, plugins, and CMake metadata into the Conan package folder.

## Dependency boundary

Qt Lottie is not an independent C++ library. It requires an existing Qt 6.11.1 installation with Qt Core, Gui, Qml, Quick, ShaderTools, and Svg components available. The recipe declares its Qt dependencies with Conan `requirements()` and lets `generate()` point CMake at the resolved Qt package folders. `CMAKE_PREFIX_PATH` is set to the `qtbase/6.11.1` package folder, with explicit `Qt6_DIR` and module `Qt6*_DIR` variables for the declared Qt dependency modules.

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

Source patches are applied in conanfile.py source() for OHOS module wiring (QuickShapesPrivate guard, lottietoqml tool gating, and lottiegenerator enablement); see manifest.yaml patches_applied.

## Tests

The upstream repository contains auto, baseline, manual, and fuzzer tests. The auto suite registers 13 CTest targets in v6.11.1 (11 shape tests, `tst_lottie_qml`, and conditional `tst_vectorimage`). All 13 targets are enabled because the qtdeclarative recipe now requires qtsvg, builds the `QtQuickVectorImageGeneratorPrivate` module, and builds/exports the `QtQuickTestUtilsPrivate` module that `tst_vectorimage` links. The `Qt6QuickTestUtilsPrivateConfig.cmake` and `libQt6QuickTestUtils.a` installs were observed in CI log `ci_3052_27979.log`; the current head additionally enables `FEATURE_quick_vectorimage`, so the conditional `tst_vectorimage` target is included. This recipe enables the Qt auto test build and runs the generated CTest suite in the OpenDesk OHOS environment. Baseline/manual visual rendering tests remain outside the headless CI gate because they require an interactive display session and image comparison baselines.

The `test_package` performs a consumer smoke test:

1. Resolves `Qt6` and the module components through the `Qt6_DIR`/`Qt6*_DIR` variables generated from the Conan dependencies.
2. Links a small executable against `Qt6::Lottie`.
3. Runs the executable, uses a Lottie JSON document embedded in `test_qtlottie.cpp` whose content is copied from the upstream fixture `tests/auto/lottie/shape/ellipse/data/ellipse_static_100x80.json`, through `Qt.labs.lottieqt`, and checks `Ready`, start/end frames, frame rate, and duration to prove the installed Qt Lottie QML module and library can be consumed.

## Verification status

The recipe uses the official source archive and SHA-256 listed in `conandata.yml`. Final OpenHarmony CI verification should run after the PR is opened:

```bash
CI_PACKAGES="archives/q/qtlottie/6.11.1" zsh ci/conan/build_and_test.sh
```

## R40 manual validation marker

Headless CI covers build, upstream Qt auto tests, linkage, and non-rendering smoke checks. Qt Lottie animation loading and rendering baseline checks still require an OpenHarmony PC display session to validate frame playback, rendering output, and EGL/GLES integration. This PR must remain at `built` status until that manual validation is complete; it must not be promoted to `published` based only on CI smoke tests.
