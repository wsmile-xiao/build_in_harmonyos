# libasd

`libasd` is a C++11 header-only library for reading high-speed AFM `.asd` files, adapted for OpenHarmony PC arm64.

- Version: 1.5.6
- Upstream: https://github.com/ToruNiina/libasd
- Conan package: `libasd/1.5.6@ohpcd/stable`

The package exports the header-only CMake target `libasd::libasd`.

The upstream release also contains a Python binding, but its top-level CMake path unconditionally expects the omitted `extlib/pybind11` submodule. This Conan package intentionally covers the documented C++ header-only component; the Python binding is not claimed.
