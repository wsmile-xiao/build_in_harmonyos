# qtspeech 6.11.1.1 OpenHarmony PC notes

## Scope

This package adapts the official Qt Speech 6.11.1 submodule for OpenHarmony PC. It builds the Qt upstream CMake project and packages the Qt TextToSpeech library and related plugin metadata.

## Dependency boundary

Qt Speech requires an existing Qt 6.11.1 installation with Qt Core, Qt Multimedia, and Qt Declarative (for the QML autotest). The recipe declares `qtbase/6.11.1`, `qtmultimedia/6.11.1`, and `qtdeclarative/6.11.1` with Conan `requirements()` and lets `generate()` point CMake at the resolved Qt package folders. `CMAKE_PREFIX_PATH` is set to the `qtbase/6.11.1` package folder, with explicit `Qt6_DIR`, `Qt6Multimedia_DIR`, `Qt6Qml_DIR`, `Qt6Quick_DIR`, `Qt6QuickTest_DIR`, and `Qt6ShaderTools_DIR` variables for the declared Qt dependency modules; `test_package` adds `Qt6TextToSpeech_DIR` for the consumer smoke test.

The recipe no longer probes system Qt prefixes; `validate()` only rejects host OSes that this HarmonyOS PC adaptation does not support.



## Build

Main CMake options:

```text
BUILD_TESTING=ON
QT_BUILD_EXAMPLES=OFF
QT_BUILD_TESTS=ON
QT_BUILD_TESTS_BY_DEFAULT=ON
CMAKE_PREFIX_PATH=<qtbase package folder (set by generate())>
Qt6_DIR/Qt6Multimedia_DIR/Qt6Qml_DIR/Qt6Quick_DIR/Qt6QuickTest_DIR/Qt6ShaderTools_DIR=<dependency package folders (set by generate())>
```

No source patch is required for the 6.11.1 baseline.

## Tests

The recipe enables the upstream Qt auto tests with `BUILD_TESTING=ON`, `QT_BUILD_TESTS=ON`, and `QT_BUILD_TESTS_BY_DEFAULT=ON`, then runs `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software ctest --test-dir <build> --output-on-failure` when target binaries can execute. Upstream `tests/auto/CMakeLists.txt` registers `tst_qtexttospeech_qml` only when `TARGET Qt::Qml AND TARGET Qt::QuickTest`; the recipe now depends on `qtdeclarative/6.11.1` and sets `Qt6Qml_DIR`, `Qt6Quick_DIR`, and `Qt6QuickTest_DIR` from that package, so all 3 CTest targets (`tst_qtexttospeech`, `tst_qtexttospeech_qml`, `tst_qvoice`) are registered. The qtdeclarative package exports `Qt6QmlConfig.cmake`, `Qt6QuickConfig.cmake`, and `Qt6QuickTestConfig.cmake` (observed in CI log `ci_3052_27979.log`). OpenDesk target logs are required before claiming the upstream pass rate.

The `test_package` performs a consumer smoke test:

1. Resolves `Qt6` and the module components through the `Qt6_DIR`/`Qt6*_DIR` variables generated from the Conan dependencies.
2. Links a small executable against `Qt6::TextToSpeech`.
3. Queries `QTextToSpeech::availableEngines()` and constructs a `QTextToSpeech` instance when the profile can execute target binaries.
4. Verifies engine selection, state/error consistency, and capability reporting. Audio backend output remains a platform validation item.

The current package scope verifies build, API linkage, and `QTextToSpeech` metadata only. It does not guarantee audible TTS output until an OpenHarmony PC speech backend is manually validated.

## Verification status

The recipe uses the official source archive and SHA-256 listed in `conandata.yml`. Final OpenHarmony CI verification should run after the PR is opened:

```bash
CI_PACKAGES="archives/q/qtspeech/6.11.1.1" zsh ci/conan/build_and_test.sh
```

## R40 manual validation marker

R40 manual validation marker: Headless CI covers build, linkage, and non-rendering smoke checks only. Qt Speech audible TTS output requires manual validation against the OpenHarmony PC speech backend. This PR must remain at `built` status until that manual validation is complete; it must not be promoted to `published` based only on CI smoke tests.
