# qthttpserver

Qt HTTP Server provides C++ APIs for embedding an HTTP server in Qt
applications.

## Available versions

| Version | Status | Build system | Dependency |
|---------|--------|--------------|------------|
| 6.11.1 | pending | CMake | qtbase-gui/6.11.1 |

## HarmonyOS PC adaptation

The Conan recipe builds the upstream Qt module against the native CMake
configuration installed by the `qtbase-gui/6.11.1` Conan package. Upstream
tests are enabled (`QT_BUILD_TESTS=ON`) and run via ctest in the build step
executed on OHOS; examples, benchmarks, and documentation are disabled. The
separate consumer test additionally constructs `QHttpServer` and checks its
initial listening-port state.

The qtbase-gui package is a mandatory publication prerequisite. Its separate
PR must be merged and published before this qthttpserver package can be merged.
