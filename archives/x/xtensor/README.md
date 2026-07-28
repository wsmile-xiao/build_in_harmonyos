# xtensor

xtensor is a C++ tensor library with NumPy-style broadcasting and lazy expression templates.

## OHOS 适配

xtensor 0.25.0 is a header-only CMake INTERFACE library. Morpheus 2.4.1 uses this exact version in its internal FetchContent fallback, so this archive provides an explicit Conan dependency path instead of allowing build-time network downloads.

## Dependencies

- xtl/0.7.7
- xsimd/13.2.0

## References

- Upstream repository: https://github.com/xtensor-stack/xtensor
- Morpheus fallback version: `3rdparty/xtensor/CMakeLists.txt` uses `XTENSOR_GIT_TAG 0.25.0`
