# lightgbm 4.6.0 OpenHarmony PC adaptation notes

## Summary

LightGBM 4.6.0 is adapted as a CMake package in CPU-only mode. Optional OpenMP, MPI, GPU, and upstream C++ tests are disabled in the base recipe to keep the package portable for OpenHarmony PC cross-build CI.

## Build and test

- Build system: CMake
- Source: `https://github.com/microsoft/LightGBM/archive/refs/tags/v4.6.0.tar.gz`
- SHA256: `71d2c25855f10e82da8cb8b0c42bdf0da56e5556ff50a93b31c0592b8932eda3`
- Disabled options: OpenMP, MPI, GPU, upstream C++ tests
- Bundled submodules: compute, eigen, fmt, fast_double_parser fetched at LightGBM v4.6.0 pinned commits
- Consumer API smoke test: compiles and links a downstream CMake project against `lightgbm::lightgbm`, includes `LightGBM/c_api.h`, creates a tiny in-memory dataset with `LGBM_DatasetCreateFromMat`, and frees it with `LGBM_DatasetFree` when host execution is available.
- CLI smoke test: runs the packaged `lightgbm --help` command when host execution is available.

The upstream `tests/cpp_tests/` CTest suite is not claimed as passed by this base PR. It is documented as an upstream test gap because it requires the full upstream test build and runtime datasets; it should be enabled in a follow-up full-test issue if the OpenHarmony CI environment can support it.
