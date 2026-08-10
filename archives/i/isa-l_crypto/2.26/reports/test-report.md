# Test Report — isa-l_crypto 2.26

## Build Verification
- Build system: CMake
- Compiler: clang 15.0.4
- Architecture: aarch64
- Build type: Release
- Status: SUCCESS

## Compilation Summary
All crypto modules compiled successfully:
- MD5 multi-buffer (ASIMD, SVE, SVE2)
- SHA1 multi-buffer (CE, ASIMD)
- SHA256 multi-buffer (CE)
- SHA512 multi-buffer (CE)
- SM3 multi-buffer (SM, SVE, SVE2, ASIMD)
- MH-SHA1 (CE, ASIMD, SVE, SVE2)
- MH-SHA256 (CE)
- MH-SHA1-Murmur3 (CE, ASIMD)
- Rolling hash
- AES-GCM/XTS/CBC (aarch64 assembly)
- FIPS self-tests

## Patches Applied
1. 0001-aes-aarch64-gcm_common.S.patch — Fix #### token-paste in FN_NAME macro

## Conan Verification
- G1 (recipe completeness): PASS
- G2 (conan create): PASS
- G3 (system library isolation): PASS
- G4 (product completeness): PASS

## W3 Local CI Simulation
- setup.sh: PASS
- build_and_test.sh: PASS

## Test Package
- test_isal_crypto: MD5 hash verification (MD5("abc") known answer test)
