# lightgbm 4.6.0 OpenHarmony PC adaptation notes

## Summary

LightGBM 4.6.0 is adapted as a CMake package in CPU-only mode. Optional OpenMP, MPI, and GPU features are disabled, while the upstream C++ test suite is kept enabled so CI at least cross-compiles those test targets for the OpenHarmony PC toolchain.

## Build and test

- Build system: CMake
- Source: `https://github.com/microsoft/LightGBM/archive/refs/tags/v4.6.0.tar.gz`
- SHA256: `71d2c25855f10e82da8cb8b0c42bdf0da56e5556ff50a93b31c0592b8932eda3`
- Disabled options: OpenMP, MPI, GPU
- Enabled validation build: upstream C++ tests via `BUILD_CPP_TEST=ON`
- Bundled submodules: compute, eigen, fmt, fast_double_parser fetched at LightGBM v4.6.0 pinned commits
- Consumer API smoke test: compiles and links a downstream CMake project against `lightgbm::lightgbm`, includes `LightGBM/c_api.h`, creates a tiny in-memory dataset with `LGBM_DatasetCreateFromMat`, and frees it with `LGBM_DatasetFree` when host execution is available.
- CLI smoke test: runs the packaged `lightgbm --help` command when host execution is available.

The upstream `tests/cpp_tests/` CTest suite is included in the package build with `BUILD_CPP_TEST=ON`, so those C++ test sources are validated by the cross compiler. Runtime execution of the full CTest suite is still not claimed in this base PR because it depends on the OpenHarmony CI runtime and upstream test data availability; the executable consumer API smoke test remains the runtime check when `can_run(self)` allows execution.
