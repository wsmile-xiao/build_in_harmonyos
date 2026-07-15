# lightgbm 4.6.0 OpenHarmony PC adaptation notes

## Summary

LightGBM 4.6.0 is adapted as a CMake package in CPU-only mode. Optional OpenMP, MPI, GPU, and C++ tests are disabled to keep the base package portable for OpenHarmony PC cross-build CI.

## Build and test

- Build system: CMake
- Source: `https://github.com/microsoft/LightGBM/archive/refs/tags/v4.6.0.tar.gz`
- SHA256: `71d2c25855f10e82da8cb8b0c42bdf0da56e5556ff50a93b31c0592b8932eda3`
- Disabled options: OpenMP, MPI, GPU, C++ tests
- Bundled submodules: compute, eigen, fmt, fast_double_parser fetched at LightGBM v4.6.0 pinned commits
- Smoke test: runs the packaged `lightgbm --help` command when host execution is available.
