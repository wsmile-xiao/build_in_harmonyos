# GEOS 3.13.0.1 OHOS adaptation notes

This is a recipe revision for the upstream GEOS 3.13.0 release.

## Scope

- Source: https://download.osgeo.org/geos/geos-3.13.0.tar.bz2
- SHA256: `47ec83ff334d672b9e4426695f15da6e6368244214971fabf386ff8ef6df39e4`
- Build system: CMake
- Package type: library plus bundled GEOS command line utilities

## Build choices

- Build static `libgeos` and `libgeos_c` by default (`BUILD_SHARED_LIBS=OFF`).
  This keeps the dependency predictable for OHOS downstream builds and avoids
  the RPATH-sensitive shared-library path noted in earlier GEOS experiments.
- Enable upstream CTest in native package builds. GEOS upstream registers 324
  `unit-*` CTest entries from `tests/unit/**/*Test.cpp` and 168 XML validation
  entries through `tests/xmltester/tests/**/*.xml`; the recipe now builds the
  upstream test executables and runs `ctest --output-on-failure --parallel 1`
  before packaging when the build is native. Cross builds skip runtime CTest
  execution because the generated test binaries target OHOS rather than the
  build host; they still verify source configuration, compilation, and link.
  The `all-unit-tests` and `all-xml-tests` aggregate entries are restricted to
  the `Valgrind` CTest configuration and are not part of the default package
  test execution. Benchmarks, website generation, and astyle remain disabled
  because they are auxiliary targets rather than adaptation correctness tests.
- Keep installed `geosop` and `geos-config`; the software-level
  `commands.json` declares the CLI side of the package.
- Expose CMake component targets `GEOS::geos` and `GEOS::geos_c`; MapServer's
  legacy `FindGEOS.cmake` can also discover the installed `geos_c` library and
  `geos_c.h` through Conan's package search paths.

## Test coverage

The `test_package` builds a real C++ consumer linked to `GEOS::geos_c` and
executes five additional package-consumer checks:

1. `GEOSversion()` reports `3.13.0`.
2. WKT polygon parsing succeeds.
3. Polygon area calculation returns 4.0 for a 2x2 square.
4. Point buffer generation produces a positive-area geometry.
5. Spatial intersection and invalid-WKT rejection work through the C API.

## Local validation

- Source SHA256 verified on Windows.
- Python recipe syntax check and repository whitespace check passed locally.
- Native CMake validation passed on Windows/MinGW with the package build
  switches (`BUILD_SHARED_LIBS=OFF`, `BUILD_TESTING=ON`, benchmarks/website/
  astyle disabled).
- Native upstream CTest validation passed on Windows/MinGW: `ctest` reported
  `100% tests passed, 0 tests failed out of 492`.
- Native install-tree consumer validation passed: the `test_package`
  CMakeLists built against the installed GEOS config package and
  `test_geos.exe` completed all five GEOS C API checks.
- Cross-building is guarded with `cross_building(self)` in both the package
  build CTest step and `test_package.test()`, so OHOS target binaries are not
  executed on the build host.
- Full `conan create geos/3.13.0.1` still requires the OHOS Conan environment;
  this workstation currently has no local `conan` command.
