# qtwebsockets 6.11.1 adaptation notes

## Build configuration

- Uses the `harmonyos-clang` Qt mkspec for OHOS builds.
- Requires `qtbase/6.11.1`.
- Reuses the native CMake package files installed by `qtbase` and by
  `qtwebsockets` instead of generating Conan CMake package wrappers.
- Enables Qt upstream tests; disables examples, benchmarks, and manual tests.
- Generates `VirtualRunEnv` so target-side Qt shared libraries are visible
  when tests run.
- Resolves `ctest` from PATH first and then from the HarmonyOS HNP CMake tool
  paths because Conan recipe commands may run under `/system/bin/sh` without
  the CMake package directory in PATH.

## Upstream tests

- Official source SHA-256:
  `243e3aa11924c8c5c1645e892f62d013caa3766c57512ca926d5b58146646fbf`.
- Under the published `qtbase/6.11.1` dependency contract, upstream CMake
  registers three public C++ auto-test targets and one CMake package
  integration test.
- `tests/auto/websockets` also contains six private auto tests, but upstream
  guards them with `QT_FEATURE_private_tests`; the published qtbase package
  reports that feature as `OFF`, so those targets are not registered.
- `tests/auto/qml/qmlwebsockets` is guarded by upstream CMake with
  `TARGET Qt::Quick AND TARGET Qt::QuickTest`; those components are not
  provided by the current published `qtbase/6.11.1` dependency contract.

## Consumer test

- Builds a CMake consumer with `find_package(Qt6 6.11.1 REQUIRED COMPONENTS
  Core Network WebSockets)`.
- Runs a local loopback `QWebSocketServer` and `QWebSocket` exchange.
- Added consumer test count: 1 test case; internal checks are reported
  separately and are not counted as additional test cases.

## Source

- URL: `https://download.qt.io/official_releases/qt/6.11/6.11.1/submodules/qtwebsockets-everywhere-src-6.11.1.tar.xz`
- SHA-256: `243e3aa11924c8c5c1645e892f62d013caa3766c57512ca926d5b58146646fbf`
