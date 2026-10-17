# cpp-jwt 1.5.1 Adaptation Notes

## Build Environment
- Build system: cmake (header-only INTERFACE library)
- Compiler: clang/clang++ 15 (HarmonyOS aarch64, libc++)
- Status: built (recipe complete; awaiting HMBS preflight conan create)

## Build Steps

```bash
# Recipe lives at archives/c/cpp-jwt/1.5.1/
# Upstream CMake options used by the recipe:
#   -DCPP_JWT_BUILD_EXAMPLES=OFF
#   -DCPP_JWT_BUILD_TESTS=ON        (full GTest suite runs in build())
#   -DCPP_JWT_USE_VENDORED_NLOHMANN_JSON=ON  (only openssl required)
#   -DGTest_DIR=<gtest package>/lib/cmake/GTest
# Build + test entry:
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# build() runs: cmake configure -> cmake build -> ctest --output-on-failure
# test_package runs: cmake configure -> cmake build -> ctest (2 binaries)
```

## Issues and Solutions

| # | Issue | Root Cause | Solution |
|---|-------|------------|----------|
| 1 | Upstream `find_package(GTest)` vs conan `gtest` naming | gtest recipe exposes `gtest::gtest`, upstream wants `GTest::*` | Pass `GTest_DIR` to the gtest package config (abseil pattern); CMake module then resolves real targets |
| 2 | Downstream `nlohmann/json.hpp` not found in test_package | VENDORED=ON only defines the macro for the upstream build; CMakeDeps consumers never get it, so installed jwt.hpp falls back to `nlohmann/json.hpp` | VENDORED=OFF (conan-center precedent) + `requires nlohmann_json/3.12.0` + native `nlohmann_json_DIR` + `package_info.requires` propagation |
| 3 | RSA/ES tests need cert files | Tests read `tests/certs` via CERT_ROOT_DIR | Upstream handles it via compile definition; no patching needed |

## Source Changes

None. No patches; upstream builds unmodified on OHOS.

## Dependencies

- openssl/3.5.8.1 (regular requires, published)
- gtest/1.17.0 (test_requires for the upstream suite only)

## Verification Results

```bash
# To be filled by HMBS preflight (real device):
# - cmake configure/build of the INTERFACE library
# - ctest: 7 upstream binaries (59 GTest TESTs)
# - test_package ctest: test_cpp-jwt + ohos_adapt_test
```

## Deliverables

| File | Description |
|------|-------------|
| conanfile.py | Header-only recipe with upstream tests enabled |
| conandata.yml | Official URL + SHA-256, no patches |
| manifest.yaml | Version manifest (cmake, built) |
| test_package/ | Consumer + OHOS tests, MANIFEST.yml |

## Notes

- R26 does not apply (header-only, no .so output to clash with system libs).
- R34: both test binaries call real jwt APIs; no stub tests.
- License MIT; headers install to include/jwt, license to licenses/.
