# Notes — zxc 0.9.1

## Build System
- CMake (CMakeLists.txt)
- Language: C (C17)
- License: BSD-3-Clause
- No external dependencies

## Source Modifications (Exploration Phase)

### 1. CMakeLists.txt — Architecture Detection Fallback
**Problem**: CMake on HarmonyOS sets `CMAKE_SYSTEM_PROCESSOR=unknown` because OHOS is not a recognized platform. The zxc CMakeLists.txt uses `CMAKE_SYSTEM_PROCESSOR` to decide whether to build architecture-specific SIMD variants (NEON for aarch64). When the processor is "unknown", no NEON variant is built, but `zxc_dispatch.c` (compiled with `__aarch64__` defined by the compiler) references the NEON symbols, causing linker errors.

**Fix**: Added a fallback detection block before the variant detection section:
```cmake
if(CMAKE_SYSTEM_PROCESSOR STREQUAL "unknown" OR NOT CMAKE_SYSTEM_PROCESSOR)
    execute_process(COMMAND uname -m OUTPUT_VARIABLE _uname_m OUTPUT_STRIP_TRAILING_WHITESPACE)
    set(CMAKE_SYSTEM_PROCESSOR "${_uname_m}")
endif()
```

**Conan Recipe Fix**: In conanfile.py `generate()`, set `CMAKE_SYSTEM_NAME=Linux` and `CMAKE_SYSTEM_PROCESSOR=aarch64` via CMakeToolchain variables to ensure proper architecture detection during conan builds.

### 2. tests/test.c — tmpfile() Replacement
**Problem**: The test code uses `tmpfile()` which creates temp files in `/tmp`, which is read-only on HarmonyOS (E002). This caused "tmpfile: Permission denied" errors and test abort.

**Fix**: Added a `zxc_tmpfile()` helper function that uses `mkstemp()` in `$TMPDIR` (with unlink for auto-cleanup, matching tmpfile() semantics). Replaced all 37 `tmpfile()` calls with `zxc_tmpfile()`. Also added `#define _GNU_SOURCE` for `mkstemp`/`fdopen` declarations.

## Build Configuration
- `BUILD_SHARED_LIBS=OFF` (R26: static linking for terminal tools)
- `ZXC_NATIVE_ARCH=OFF` (disable -march=native for portability)
- `ZXC_ENABLE_LTO=OFF` (disable LTO for compatibility)

## Test Results
- ctest: 100% tests passed (1/1) — 0.37 sec
- All round-trip compression/decompression tests pass
- CLI binary (`zxc --version`) works correctly

## Conan Recipe
- Build system: CMake (not Autotools)
- License: BSD-3-Clause (not MIT)
- `package_info()`: cpp_info.libs = ["zxc"], cpp_info.defines = ["ZXC_STATIC_DEFINE"]
- `generate()`: CMakeToolchain with BUILD_SHARED_LIBS=OFF, ZXC_NATIVE_ARCH=OFF, ZXC_ENABLE_LTO=OFF, CMAKE_SYSTEM_NAME=Linux, CMAKE_SYSTEM_PROCESSOR=aarch64
- conan-verify: ALL PASS (G0-G4, L2/L4/L5)
---

**编译结束**: 2026-06-29 15:01
**最终状态**: published
