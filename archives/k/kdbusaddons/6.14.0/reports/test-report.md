# Test Report — kdbusaddons 6.14.0

## Build

- Build system: cmake (Ninja)
- Compiler: clang 15.0.4 (HarmonyOS PC toolchain, aarch64)
- Profile: ohos-aarch64
- Configure: KF_IGNORE_PLATFORM_CHECK=TRUE, WITH_X11=OFF, BUILD_TESTING=OFF, C++20
- Result: SUCCESS

## Tests

### Upstream Tests (make check)

- Command: `ctest` in build dir (upstream autotests need a running D-Bus session bus)
- Result: **沙箱实测 2/2 通过** — 在本机 OHOS 沙箱内自建 dbus-daemon 1.14.10 + abstract session bus，
  实际编译并运行 kdbusservicetest（exit 0）与 deadservicetest（3 passed, 0 failed）。
  详见 `reports/dbus-autotests-run.md`。
- 配方保持 BUILD_TESTING=OFF（CI 沙箱无 dbus-daemon，详见 notes.md）

### Conan test_package

- Test: `test_kdbusaddons` (CMake consumer test)
- Source: `test_package/test.cpp`
- Assertions: 3
  1. `KDEDModule::moduleForMessage()` resolves a module from a D-Bus message signature
  2. `KDEDModule::setModuleName()/moduleName()` round-trip works
  3. module construction with nullptr config succeeds
- Result: PASS (1/1 tests passed, 0 failed)

### W3 Local CI Simulation

- Script: `ci/conan/build_and_test.sh`
- L0 Quality Gates: PASS (all gates including stub_test_method)
- L1e destructive negative test: PASS
- L5 SONAME gate: PASS (libKF6DBusAddons.so.6.14.0 has DT_SONAME=libKF6DBusAddons.so.6, versioned symlink chain installed)

## Artifacts

- Library: libKF6DBusAddons.so (shared, with .so.6/.so.6.14.0 symlinks)
- Binary: bin/kquitapp6
- Headers: include/KF6/KDBusAddons/
- CMake config: lib/cmake/KF6DBusAddons/

## Summary

All tests passed. Package is ready for submission.
