# Test Report — hidapi 0.14.0

## Build Environment
- Build system: CMake
- Compiler: clang 15.0.4
- Platform: OpenHarmony (OHOS) aarch64
- Date: 2026-08-07

## Build Result
- **Status**: SUCCESS
- Build options: `-DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DHIDAPI_NO_ICONV=ON`
- Output: libhidapi-libusb.so (shared library)
- Dependencies: libusb/1.0.27 (from conan remote ohpcd)

## Test Result
- **Conan test_package**: PASS
  - test_hidapi binary built and linked successfully
  - Test calls real hidapi API: hid_version_str(), hid_init(), hid_enumerate(), hid_exit()
  - hid_init() fails on headless system (expected) - test handles gracefully

## Conan Verify Report
- G0 (pre-build risk): PASS
- G1 (recipe completeness): PASS
- G2 (conan create clean build): PASS
- G3 (system lib isolation R26): PASS
- G4 (product integrity): PASS
- L2/L4/L5 (smoke test/security/baseline): PASS

## W3 Local CI Simulation
- setup.sh: PASS
- build_and_test.sh: PASS
