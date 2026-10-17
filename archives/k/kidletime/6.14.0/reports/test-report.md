# Test Report — kidletime 6.14.0

## Build

- Build system: cmake (Ninja)
- Compiler: clang 15.0.4 (HarmonyOS PC toolchain, aarch64)
- Profile: ohos-aarch64
- Configure: KF_IGNORE_PLATFORM_CHECK=TRUE, WITH_X11=OFF, WITH_WAYLAND=OFF, C++20, SONAME flags
- Result: SUCCESS

## Tests

### Conan test_package

- Test: `test_kidletime` (CMake consumer test)
- Source: `test_package/test.cpp`
- Assertions: 3 (KIdleTime::instance() non-null, version macro check, idleTime() called)
- Result: PASS (1/1 tests passed, 0 failed)

### W3 Local CI Simulation

- Script: `ci/conan/build_and_test.sh`
- L0 Quality Gates: PASS
- L1e destructive negative test: PASS
- L5 SONAME gate: PASS (libKF6IdleTime.so.6.14.0 has DT_SONAME + versioned symlinks)

## Artifacts

- Library: libKF6IdleTime.so (shared, .so.6/.so.6.14.0 symlinks)
- Headers: include/KF6/KIdleTime/
- CMake config: lib/cmake/KF6IdleTime/

## Notes

- All poller backends (X11/Wayland) disabled on OHOS; idleTime() returns 0 without a system poller. Needs manual confirmation of adaptation completeness (R40).
