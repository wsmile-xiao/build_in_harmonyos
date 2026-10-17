# xtl

xtl is a small collection of C++ utilities used by the xtensor stack.

## OHOS 适配

xtl 0.7.7 is a header-only CMake INTERFACE library. The package installs headers, CMake config files, and pkg-config metadata. For OHOS, the Conan recipe sets `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY` following E191 because no executable link test is needed for this header-only package.

## Dependencies

No required Conan dependencies.

## References

- Upstream repository: https://github.com/xtensor-stack/xtl
- Morpheus fallback version: `3rdparty/xtensor/CMakeLists.txt` uses `XTL_GIT_TAG 0.7.7`
