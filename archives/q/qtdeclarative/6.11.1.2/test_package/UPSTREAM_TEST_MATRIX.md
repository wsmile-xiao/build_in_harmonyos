# Qt Declarative 6.11.1 upstream test matrix

## Scope and execution contract

- Upstream source: `https://code.qt.io/cgit/qt/qtdeclarative.git`
- Upstream tag: `6.11.1`
- Inventory root: `tests/auto/`
- Review inventory count (`N`): `10372` files, `550` CMakeLists files and
  `22` top-level areas.
- `QT_BUILD_TESTS=ON` and `QT_BUILD_TESTS_BY_DEFAULT=ON` are enabled.
- The recipe builds every upstream test target enabled by the Qt CMake graph
  with serial `-j1` and runs the complete generated CTest registry:

```text
cd <build-folder>
ctest -N --no-tests=error
ctest --output-on-failure --no-tests=error
```

There is no fixed target allow-list and no `-R` filter. The CI log is the
authoritative record of registered, passed, failed and skipped CTest cases.
The separate Conan `test_package` consumer smoke test is reported separately
and is not added to the upstream denominator.

## Inventory interpretation

`UPSTREAM_TEST_INVENTORY.md` is a source-file inventory. A CMakeLists file,
fixture, blacklist, data file or harness support file is not itself an
independent executable CTest case. Such files are included in the upstream
source scope and their target registration is controlled by the upstream
CMake graph. The inventory records the first applicable gate so that a CTest
registration or build omission is visible and cannot be silently reported as
passing.

## Upstream CMake/runtime gates

| Area | Gate or dependency recorded for CI |
|---|---|
| `bic` | ABI/compiler baseline fixtures; no standalone runtime executable |
| `cmake` | Qt BuildInternals, host CMake and generated-project harness |
| `coin` | CI orchestration metadata, not a native CTest binary |
| `core` | Device filesystem, settings backend and system-service state |
| `guiapplauncher` | GUI example launch and window backend |
| `qml` core/language families | Generated QML data, private targets, plugins and import paths |
| `qml` tooling | Host tools, installed QML modules, subprocess/IPC and generated code |
| `qml` debugger | Process support, QML debug service and debugger IPC |
| `qmldom` / `qmlls` | Private Qt targets, host subprocesses and JSON-RPC/IPC |
| `qmlnetwork` | OS network services, SSL/OpenSSL and network-information backend |
| `qmltest` / `quicktest` | QML test runner, QPA, event loop, windows and input |
| `particles` / `quick` | Qt Quick scene graph, QPA, RHI/OpenGL and graphics backend |
| `quickcontrols` / `quickdialogs` | Templates, style assets, native dialogs and platform UI |
| `quickshapes` / `quickvectorimage` | Graphics/RHI support and Qt Svg where required |
| `quickwidgets` | Qt Widgets and QtQuickWidgets runtime |
| `qtquickview` | Android Gradle/JNI/Activity integration; not native PC |
| `wasm` | Emscripten, browser, HTML hosting and Selenium harness |

These are upstream gates, not an exemption list. The CI recipe attempts the
whole CMake-enabled CTest graph and preserves the concrete result when a gate
causes a target to be unregistered, fail to build or fail at runtime.

## Known packaging constraints under test

- HarmonyOS PC CMake does not provide `Platform/HarmonyOS.cmake`; the recipe
  presents Linux platform rules while retaining the OHOS clang target triple.
- HMDFS rejects symlink creation and jobserver FIFOs. The recipe materializes
  CMake library aliases and serializes the complete build with `-j1`.
- `qsb` from `qtshadertools` needs `qtbase/lib` and `qtshadertools/lib` in
  `LD_LIBRARY_PATH` during shader generation.
- OHOS ELF binaries must be signed before real-device execution.
- QML import and platform plugin paths are exported for the full test run.

## Result accounting

Do not copy a historical subset result into the full-run result. For each CI
or shadow run, record:

1. CTest registered count from `ctest -N`.
2. Passed, failed, skipped and not-run counts from the final CTest summary.
3. Build failures before CTest registration.
4. The separate `test_package` result.

An upstream pass-rate claim is valid only when it uses those same-run CTest
totals. The recipe intentionally fails the Conan build when the complete
CTest command returns non-zero.
