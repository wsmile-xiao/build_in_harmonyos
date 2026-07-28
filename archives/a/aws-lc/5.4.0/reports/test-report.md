# Test Report — aws-lc 5.4.0

## Build Test

| Phase | Result | Notes |
|-------|--------|-------|
| cmake configure | PASS | "System is unknown to cmake" warnings (non-blocking) |
| cmake build | PASS | 100% targets built, libcrypto.a + libssl.a produced |
| cmake install | PASS | Libraries + headers + pkgconfig installed |
| conan create | PASS | G2 clean build verification passed |
| conan-verify G1-G4+L2/L4/L5 | ALL PASS | All 8 gates passed |
| W3 local CI simulation | PASS | setup.sh + build_and_test.sh passed |

## Test Package

- test_package/test.c: SHA-256 known-answer test using aws-lc libcrypto API
- Linked against libcrypto.a (static, R26)
- PASS: SHA-256("abc") matches expected digest

## Notes

- BUILD_TESTING=OFF: C++ test executables (rwlock_static_init etc.) fail to link libc++ on HarmonyOS
  - Library targets (libcrypto.a, libssl.a) build correctly without test executables
  - This is a platform limitation, not a library issue
- OPENSSL_NO_ASM=ON: Required because CMAKE_SYSTEM_PROCESSOR is "unknown" on HarmonyOS
  (uname -p returns "unknown"), causing ARCH to be "generic" without defining OPENSSL_NO_ASM
  - Pure-C implementations used instead of assembly
  - Performance impact is acceptable for first adaptation
- DISABLE_GO=ON: Go not available on HarmonyOS, aws-lc uses pre-generated code
- No source patches required
