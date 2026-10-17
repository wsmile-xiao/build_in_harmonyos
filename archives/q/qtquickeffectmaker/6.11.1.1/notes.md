# qtquickeffectmaker 6.11.1 OpenHarmony PC notes

## Scope

This package adapts the official Qt Quick Effect Maker 6.11.1 submodule for OpenHarmony PC. It builds the Qt upstream CMake project and packages the qqem tool, the QtQuickEffectMaker QML node assets, and installed Qt metadata. Upstream 6.11.1 does not build a `libQt6QuickEffectMaker` shared library or a `Qt6QuickEffectMaker` CMake component, so the recipe does not fabricate or consume one.

## Dependency boundary

Qt Quick Effect Maker requires an existing Qt 6.11.1 installation with Qt Core, Gui, Qml, Quick. The recipe declares its Qt dependencies with Conan `requirements()` and lets `generate()` point CMake at the resolved Qt package folders. `CMAKE_PREFIX_PATH` is set to the `qtbase/6.11.1` package folder, with explicit `Qt6_DIR` and module `Qt6*_DIR` variables for the declared Qt dependency modules.

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

`source()` patches `tests/auto/CMakeLists.txt` to drop the `NOT CMAKE_CROSSCOMPILING` guard, so the upstream `tst_qtquickeffectmaker` CTest target is registered in OHOS cross builds as well as native builds. `generate()` additionally presents the target as Linux (`CMAKE_CROSSCOMPILING=FALSE`) so upstream's top-level cross-compiling guard does not skip the module build.

## Tests

The recipe enables the upstream Qt auto tests with `BUILD_TESTING=ON`, `QT_BUILD_TESTS=ON`, and `QT_BUILD_TESTS_BY_DEFAULT=ON`, then runs `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software ctest --test-dir <build> --output-on-failure` when target binaries can execute. The source patch registers `tst_qtquickeffectmaker` even when the OHOS toolchain would otherwise set `CMAKE_CROSSCOMPILING=TRUE`. OpenDesk target logs are required before claiming the upstream pass rate.

The `test_package` performs a consumer smoke test:

1. Resolves `Qt6` and the module components through the `Qt6_DIR`/`Qt6*_DIR` variables generated from the Conan dependencies.
2. Links the executable against the Qt6 Core/Gui/Qml/Quick targets that upstream actually provides.
3. Verifies that the installed `qqem` tool binary is packaged from the module.
4. Runs the consumer executable with the packaged `qqem` path so the test binary executes `qqem --help` when the profile can execute target binaries, or verifies target binary metadata for cross profiles.

The packaged `qqem` executable is treated as an offline effect-authoring tool in this package smoke test, so the automated check verifies the tool can start and print help without requiring a display session. Shader-effect rendering still depends on the Qt Quick scene graph and must be manually validated on an OpenHarmony PC display session.

## Verification status

The recipe uses the official source archive and SHA-256 listed in `conandata.yml`. Final OpenHarmony CI verification should run after the PR is opened:

```bash
CI_PACKAGES="archives/q/qtquickeffectmaker/6.11.1.1" zsh ci/conan/build_and_test.sh
```

## R40 manual validation marker

R40 manual validation marker: Headless CI covers build, linkage, upstream auto tests, and non-rendering smoke checks only. Qt Quick Effect Maker shader generation and rendered effect output require an OpenHarmony PC display session with Qt Quick scene graph support. This PR must remain at `built` status until that manual validation is complete; it must not be promoted to `published` based only on CI smoke tests.
