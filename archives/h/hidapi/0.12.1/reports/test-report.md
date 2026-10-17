# Test Report — hidapi 0.12.1

## Build Environment
- Build system: CMake
- Compiler: clang 15.0.4
- Platform: OpenHarmony (OHOS) aarch64
- Date: 2026-08-11

## Build Result
- **Status**: SUCCESS
- Source: hidapi-0.12.0.tar.gz (SHA256: 28ec1451f0527ad40c1a4c92547966ffef96813528c8b184a665f03ecbb508bc)
- Build options: `-DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DHIDAPI_NO_ICONV=ON -DHIDAPI_WITH_LIBUSB=OFF -DHIDAPI_WITH_HIDRAW=ON`
- Output: libhidapi-hidraw.a (static library, hidraw backend only)
- Dependencies: libudev-zero/1.0.4 (from conan remote ohpcd)

## Test Result
- **Conan test_package**: PASS
  - test_hidapi binary built and linked successfully
  - Test calls real hidapi API: hid_init(), hid_enumerate(), hid_free_enumeration(), hid_exit()
  - Output: `test hidapi 0.12: OK`
- **Upstream test suite**: hidapi 0.12 has no independent test suite (hidtest/test.c is example program only, CMakeLists.txt has no enable_testing)
  - test_package covers equivalent real-API verification

## Conan Verify Report
- G0 (pre-build risk): PASS
- G1 (recipe completeness): PASS
- G2 (conan create clean build): PASS
- G3 (system lib isolation R26): PASS
- G4 (product integrity): PASS
- L2/L4/L5 (smoke test/security/baseline): PASS

## W3 Local CI Simulation
- setup.sh: PASS
- build_and_test.sh hidapi/0.12.1: PASS

## Patches Applied
- 0001-src-CMakeLists.txt.patch: system name match `Linux` → `Linux|HarmonyOS|OHOS`, else branch no longer forces libusb backend
