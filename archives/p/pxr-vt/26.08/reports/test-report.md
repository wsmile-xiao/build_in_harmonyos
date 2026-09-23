# Test Report: pxr-vt 26.08

## Build Verification

- Build system: Conan 2 + CMake
- Profile: ohos-aarch64 (clang 15, armv8, libc++, C++17, Release)
- Build target: vt (pulls in arch, tf, gf, trace, work)
- Result: **PASS** - All libraries built successfully

## Test Results

### Conan Test Package (L1)
- Test binary: test_pxr_vt
- Test result: **PASS**
- Output: `pxr-vt smoke test: OK`

### Test Coverage
- VtValue: integer and string holding/get - PASS
- VtArray: creation and value holding - PASS
- VtDictionary: key insertion and lookup - PASS

## Patches Applied

1. `pxr/base/arch/assumptions.cpp` - _SC_LEVEL1_DCACHE_LINESIZE guard
2. `pxr/base/arch/errno.cpp` - POSIX strerror_r compatibility
3. `pxr/base/arch/stackTrace.cpp` - __environ to environ
4. `pxr/base/tf/atomicRenameUtil.cpp` - DEFFILEMODE guard

## Dependencies
- tbb/2023.0.0 - resolved from ohpcd remote
