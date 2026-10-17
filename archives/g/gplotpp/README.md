# GPLOT++ (gplotpp)

GPLOT++ is a C++17 header-only library providing a high-level interface to
[Gnuplot](http://www.gnuplot.info/). It has no compiled artifacts: a single
`gplot++.h` header plus the CMake package config files.

## HarmonyOS adaptation

- The upstream v1.1.0 CMake INTERFACE project is used as-is with no patches.
- gplotpp is header-only and has no third-party Conan dependencies.
- The package installs `gplot++.h` and the CMake config, exposing the
  canonical `gplotpp::gplotpp` consumer target through Conan metadata.
- The upstream doctest suite (2 `TEST_CASE`s in `tests/src/run_tests.cpp`)
  requires the real `gnuplot` executable at runtime; the recipe and the
  consumer test locate it from PATH or the ohpcd registry cache
  (gnuplot/6.0.3) and run the full suite.
- A HarmonyOS-specific test (`test_ohos`) compiles and runs a real consumer
  against the installed header on the device: ELF aarch64, musl libc, no
  host path leakage, and a real plot rendered to SVG with label checks.

## References

- https://github.com/ziotom78/gplotpp
- https://github.com/ziotom78/gplotpp/releases/tag/v1.1.0