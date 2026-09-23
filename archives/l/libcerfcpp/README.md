# libcerfcpp

`libcerfcpp` is the C++ interface of the libcerf numeric library adapted for OpenHarmony PC arm64.

- Version: 3.3
- Upstream: https://jugit.fz-juelich.de/mlz/libcerf
- Conan package: `libcerfcpp/3.3@ohpcd/stable`

The package exposes `cerf::cerfcpp` from `find_package(cerf CONFIG REQUIRED)` and links `libcerfcpp` (plus system `m`).
