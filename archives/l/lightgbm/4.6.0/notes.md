# lightgbm 4.6.0 OpenHarmony PC adaptation notes

## Summary

LightGBM 4.6.0 is adapted as a CMake package in CPU-only mode. Optional OpenMP, MPI, and GPU features are disabled, while the upstream C++ test suite is enabled and executed during the Conan build on OpenHarmony PC.

## Build and test

- Build system: CMake
- Source: `https://github.com/microsoft/LightGBM/archive/refs/tags/v4.6.0.tar.gz`
- SHA256: `71d2c25855f10e82da8cb8b0c42bdf0da56e5556ff50a93b31c0592b8932eda3`
- Disabled options: OpenMP, MPI, GPU
- Enabled validation build: upstream C++ tests via `BUILD_CPP_TEST=ON`
- Upstream runtime validation: recipe registers `testlightgbm` with CTest and runs `ctest --test-dir <build> --output-on-failure`
- Bundled submodules: compute, eigen, fmt, fast_double_parser fetched at LightGBM v4.6.0 pinned commits
- Consumer API smoke test: compiles and links a downstream CMake project against `lightgbm::lightgbm`, includes `LightGBM/c_api.h`, creates a tiny in-memory dataset with `LGBM_DatasetCreateFromMat`, and frees it with `LGBM_DatasetFree` when host execution is available.
- CLI package check: verifies the packaged `lightgbm` executable is installed when host execution is available.
- Declared package test pass rate: final upstream CTest and test_package pass counts are taken from OpenDesk/CI logs for the current head.

The upstream `tests/cpp_tests/` suite is included with `BUILD_CPP_TEST=ON`. LightGBM v4.6.0 creates a `testlightgbm` executable but does not register it with CTest by default, so the recipe patches the upstream CMakeLists to add `add_test(NAME testlightgbm COMMAND $<TARGET_FILE:testlightgbm>)` and runs it from the upstream source root before running CTest. This prevents the misleading `No tests were found` result, keeps upstream example data discoverable, and records the real upstream runtime outcome.
