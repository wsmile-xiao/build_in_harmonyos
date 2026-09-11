# libcifpp 9.0.6 Adaptation Notes

## Key Challenges

### 1. std::from_chars for float unavailable
OHOS clang 15 libc++ does not support `std::from_chars` for floating point types.
The CMakeLists.txt's `try_compile` detects this and falls back to FastFloat.
- Used `fast_float/7.0.0` from Conan (instead of upstream FastFloat 8.0 which is not in registry)
- Patched CMakeLists.txt to remove version constraint: `find_package(FastFloat 8.0 QUIET CONFIG)` → `find_package(fast_float QUIET CONFIG)`
- Patched target name: `FastFloat::fast_float` → `fast_float::fast_float`

### 2. std::format unavailable
OHOS libc++ defines `_LIBCPP_HAS_NO_INCOMPLETE_FORMAT`, making `std::format` unavailable
even though `#include <format>` succeeds. The header exists but the function is disabled.
- Added `fmt/8.1.1` as a Conan dependency
- Patched `include/cif++/format.hpp` to always use `#include <fmt/format.h>` and `using fmt::format;`
- Patched all source files that used `std::format` directly to use `fmt::format`

### 3. Aggregate initialization in construct_at
OHOS libc++ `std::construct_at` does not support aggregate initialization (P0960).
- `key_element_type` (aggregate struct) used with `vector::emplace_back` failed
- Patched `include/cif++/category.hpp` to add explicit constructors

### 4. CMake target name mismatches
Conan CMakeDeps generates lowercase target names, but CMakeLists.txt uses uppercase:
- `ZLIB::ZLIB` → `zlib::zlib`
- `find_package(ZLIB QUIET)` → `find_package(ZLIB QUIET CONFIG)` (force config mode to use CMakeDeps)

### 5. pcre2 via pkg_check_modules
CMakeLists.txt uses `pkg_check_modules` (not `find_package`) for pcre2.
- Used `PkgConfigDeps` generator alongside `CMakeDeps` in conanfile.py
- No CMakeLists.txt patch needed for pcre2

### 6. CCD download and update script
- `CIFPP_DOWNLOAD_CCD=OFF` - prevents 300MB download from wwPDB
- `CIFPP_INSTALL_UPDATE_SCRIPT=OFF` - prevents FATAL_ERROR on non-Linux/GNU/FreeBSD systems

## Dependencies
- zlib/1.3.1
- eigen/3.4.0
- pcre2/10.45.1
- fast_float/7.0.0
- fmt/8.1.1
---

**编译结束**: 2026-09-10 16:28
**最终状态**: built
