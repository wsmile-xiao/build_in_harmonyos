# Build Notes — lzfse 1.0

## Build Process

### Build System
- Build system: CMake (CMakeLists.txt)
- The lzfse repo also has a Makefile, but CMake provides better Conan integration
- No configure step needed (CMake-based)

### CMake Compatibility Fix
- lzfse's CMakeLists.txt declares `cmake_minimum_required(VERSION 2.8.6)`
- CMake 4.x removed compatibility with versions < 3.5
- Fix: Set `CMAKE_POLICY_VERSION_MINIMUM=3.5` in CMakeToolchain (no source patch needed)

### Build Commands
```bash
cd build_dir
cmake -B build -DCMAKE_TOOLCHAIN_FILE=generators/conan_toolchain.cmake \
      -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
      -DLZFSE_DISABLE_TESTS=ON
cmake --build build
cmake --install build
```

### Products
- Static library: `liblzfse.a`
- Command line tool: `lzfse`
- Header: `lzfse.h`

### Dependencies
- None

### Platform Notes
- HarmonyOS not recognized by CMake as a platform (E092 warning), but compilation works fine
- CMake detects Clang 15.0.4 correctly
- Binary signing handled by CI pipeline (sign.sh)

## Verification
- conan create passed (G2)
- Round-trip encode/decode test via lzfse_encode_buffer/lzfse_decode_buffer
- Static library isolation verified (G3, R26)
---

**编译结束**: 2026-07-15 16:30
**最终状态**: built
