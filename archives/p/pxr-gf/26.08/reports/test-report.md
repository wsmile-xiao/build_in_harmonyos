# Test Report: pxr-gf 26.08

## Build Verification

- Build system: Conan 2 + CMake
- Profile: ohos-aarch64 (clang 15, armv8, libc++, C++17, Release)
- Build target: gf (pulls in arch, tf)
- Result: **PASS** - libusd_gf.a, libusd_tf.a, libusd_arch.a built successfully
- W3 local CI simulation (build_and_test.sh): **PASS** (L0/L1/L2/L4/L5 all green)

## Test Results

### Conan Test Package (L1)
- Test binary: test_pxr_gf
- Test result: **PASS**
- Output: `pxr-gf smoke test: OK (ArchStrerror(ENOENT)="No such file or directory")`

### Test Coverage
- GfVec3d: construction and component access - PASS
- GfMatrix4d: diagonal construction and determinant - PASS
- GfRotation: axis/angle construction and TransformDir - PASS
- ArchStrerror: exercises patched POSIX strerror_r path on OHOS - PASS
- TfGetenv: exercises tf foundation library - PASS

## Patches Applied

1. `pxr/base/arch/assumptions.cpp` - _SC_LEVEL1_DCACHE_LINESIZE feature guard (fallback 64)
2. `pxr/base/arch/errno.cpp` - POSIX strerror_r compatibility (drop _GNU_SOURCE branch)
3. `pxr/base/arch/stackTrace.cpp` - __environ to environ
4. `pxr/base/tf/atomicRenameUtil.cpp` - DEFFILEMODE/ACCESSPERMS guards

All guards are feature-based (no __OHOS__ platform macros), identical to the
proven patch shipped with pxr-vt/26.08 from the same upstream tarball.

## Dependencies
- tbb/2023.0.0 - resolved from ohpcd remote (binary package 6b129b068851896169fae42d399fa922d239ce8a)
