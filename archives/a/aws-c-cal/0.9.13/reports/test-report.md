# Test Report — aws-c-cal 0.9.13

## Build
- Status: SUCCESS
- Build system: CMake
- Compiler: clang 15.0.4
- Build type: Release
- Static library: libaws-c-cal.a

## Test Results
- Test method: Conan test_package (L1)
- Test status: PASSED
- Test details: aws-c-cal library symbols resolved, initialization and cleanup verified

## Dependencies
- aws-c-common/0.12.6 (static)
- aws-lc/5.4.0 (static, crypto backend)

## Verification
- conan-verify: G1 PASS, G2 PASS, G3 PASS, G4 PASS
- W3 CI simulation: PASS
