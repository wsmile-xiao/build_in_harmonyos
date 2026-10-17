# astc-encoder 5.7.0 adaptation notes

## Scope

- Branch: `feat/astc-encoder-5.7.0`
- Adaptation path: `archives/a/astc-encoder/5.7.0`

## W0 Dependency Check

- astc-encoder is fully self-contained with no external library dependencies.
- The only submodule is GoogleTest (`Source/GoogleTest`), used only when `ASTCENC_UNITTEST=ON`.
- GoogleTest v1.14.0 is downloaded manually in `conanfile.py source()` method.
- No missing mandatory dependencies; W0 passes.

## Source And Build System

- Source URL: `https://github.com/ARM-software/astc-encoder/archive/refs/tags/5.7.0.tar.gz`
- SHA256: `7c1b28ece59c9c2737e297123a9910c1c548676c7aed87a09d5734e2fa7bdaf0`
- Build system: CMake (minimum 3.15), C++14 standard
- License: Apache-2.0
- Patches: none

## ISA Selection

On OHOS/aarch64:
- `ASTCENC_ISA_NEON=ON` — use ARM NEON SIMD
- All x86 ISA options (SSE2, SSE41, AVX2) explicitly OFF
- `ASTCENC_NATIVE=OFF` — do not auto-detect

## Recipe Strategy

- Static library by default (`ASTCENC_SHAREDLIB=OFF`)
- CLI tool enabled (`ASTCENC_CLI=ON`)
- Unit tests enabled (`ASTCENC_UNITTEST=ON`) — GoogleTest downloaded in source()
- Warnings-as-errors disabled (`ASTCENC_WERROR=OFF`) — clang 15 differences
- Floating point invariance enabled (`ASTCENC_INVARIANCE=ON`)
- Compiler: `clang-15` (via OHOS SDK wrapper)

## OHOS-specific Adaptation Notes

### LLVM lld and libxml2.so.16

clang-15 on OHOS defaults to using LLVM lld as the linker. The lld binary at
`/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/lld`
requires `libxml2.so.16` at runtime. The library exists at:
`/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/libxml2.so.16`

Solution: Set `LD_LIBRARY_PATH` to include the SDK lib directory before running
cmake/make:
```
export LD_LIBRARY_PATH="/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:..."
```

### LTO (Link-Time Optimization)

Upstream CMake enables LTO for CLI targets (`INTERPROCEDURAL_OPTIMIZATION_RELEASE=True`).
LTO generates LLVM bitcode object files that require lld (not GNU ld) for linking.
Using lld with the correct LD_LIBRARY_PATH resolves this.

### Upstream CMake Install Gap

Upstream CMake only installs the CLI binary (`astcenc-neon`). The static library and
public header are NOT installed. The Conan recipe's `package()` method manually copies:
- `libastcenc-neon-static.a` → `lib/`
- `astcenc.h` → `include/`
- `astcenc-neon` → `bin/`

## Products

- `lib/libastcenc-neon-static.a` — static library (372,126 bytes)
- `include/astcenc.h` — public header
- `bin/astcenc-neon` — CLI compression tool (662,016 bytes)

## Test Strategy

### Upstream C++ Unit Tests (GoogleTest)

- `ASTCENC_UNITTEST=ON` enables C++ unit tests via GoogleTest
- Tests: `test_simd.cpp`, `test_softfloat.cpp`, `test_decode.cpp`, `test_encode.cpp`
- Built as `test-unit-neon` executable
- Executed via `ctest --output-on-failure`
- Result: **1/1 tests passed** (test-unit-neon)

### Consumer Test (test_package)

- `test_package/test_astcenc.cpp` performs a consumer smoke test: config init, context
  alloc, compress+decompress round-trip on a 4x4 RGBA image (5 assertions)

## Manual Build Verification

```bash
cd $BUILD_SRC_DIR
mkdir -p Source/GoogleTest && cd Source/GoogleTest
# Download GoogleTest v1.14.0
curl -L -o gtest.tar.gz https://github.com/google/googletest/archive/refs/tags/v1.14.0.tar.gz
tar xzf gtest.tar.gz --strip-components=1
cd ../..
mkdir build && cd build
export LD_LIBRARY_PATH="/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:..."
cmake .. -DCMAKE_BUILD_TYPE=Release -DASTCENC_ISA_NEON=ON -DASTCENC_CLI=ON \
  -DASTCENC_WERROR=OFF -DASTCENC_UNITTEST=ON \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++
make -j1
ctest --output-on-failure
```

CMake build results:
- `libastcenc-neon-static.a`: 372,126 bytes ✅
- `astcenc-neon` CLI: 662,016 bytes ✅
- `astcenc-neon -help`: "astcenc v5.7.0, 64-bit neon" ✅
- `ctest`: 1/1 tests passed ✅

## Differences from 5.3.0

- 5.7.0 adds `test_encode.cpp` unit test (not in 5.3.0)
- 5.7.0 uses GoogleTest v1.14.0 (5.3.0 didn't specify version)
- Build artifacts have same names as 5.3.0 (ISA-suffixed)
- API is backward-compatible with 5.3.0
