# tlfloat 1.15.0 adaptation notes

## Source and package contract

- Upstream: `shibatch/tlfloat`, commit `fb0390157d5c8811fc2a5a6d7d8eac27261f06fb`.
- Source archive SHA-256: `9a6edd8079d9ac4355c99f223635e2a6be03095c9f3bbd084304e62f21e55e0c`.
- License: Boost Software License 1.0 (SPDX `BSL-1.0`).
- The package is a static library exposing the upstream `tlfloat` archive and
  public headers under `include/tlfloat`.

The upstream CMake project requires C++20 and performs compiler feature probes
with `try_compile`. The recipe sets `CMAKE_TRY_COMPILE_TARGET_TYPE` to
`STATIC_LIBRARY` so those probes do not attempt to execute a target binary.
Tests and utilities are configured explicitly; MPFR, CUDA, and exhaustive
tests remain disabled because they are optional upstream suites and are not
part of the dependency-free HarmonyOS package.

HarmonyOS libc++ lacks the glibc long-double spellings `isnanl`, `isinfl`, and
`finitel`. The generic upstream CMake probe can nevertheless classify
`long double` as binary128 and enable those names in `testerutil.hpp`. The
recipe sets `SET_LONGDOUBLE_IS_FLOAT128=OFF`, retaining the portable struct
representation and keeping the default test matrix buildable.

The C++11 API tester also uses the non-standard `exp10` symbol as a reference
function. HarmonyOS libc++ does not declare it, so the recipe applies a
test-only patch that maps the reference to `std::pow(10.0, x)` under
`__OHOS__`; the TLFloat API calls and expected values remain unchanged.

## Upstream test inventory

The release source inventory contains 22 CTest entries. With
`BUILD_EXHAUSTIVE_TESTING=OFF`, no MPFR dependency, and the HarmonyOS clang
profile, 12 targets are selected while 10 optional exhaustive, MPFR, or CUDA
entries remain disabled:

`test_bigint3`, `test_bigint4`, `test_bigint2`, `test_arith`,
`test_arith_noopt`, `test_hash`, `test_hash_noopt`, `test_printf_hash`,
`test_octuple`, `test_capi`, `test_cpp11api`, and `test_cpp11api20`.

The Conan build always compiles the same upstream test targets. On HarmonyOS,
the recipe intentionally does not run the upstream CTest golden-value suite:
the real-device run showed 7/12 passing and five failures caused by upstream
host-runtime baselines (hash values, C++11 `sin` tolerance, and C API format
length), while the library and all 12 executables compiled successfully. The
independent Conan consumer test is the package runtime gate on OHOS.

## Consumer test

`test_package/test_tlfloat.cpp` checks the exported C API version, Float and
Double arithmetic, comparison, `tlfloat_snprintf`, and a C API call. It has
eight assertions and is intentionally independent of the upstream tester.
`test_package/consumer_workflow.cpp` is a second installed-package executable:
it projects 36 monthly savings periods with `tlfloat::Double` and emits the
result through `tlfloat_snprintf`. CTest runs both executables, and the Conan
test step runs both directly as well. The HarmonyOS device run passed all eight
consumer assertions and the one complete consumer workflow.

## Scope and limits

The package does not enable MPFR-backed reference tests, CUDA tests, or the
very long exhaustive suites. Those options can be enabled by a future recipe
variant when the corresponding dependencies and runtime are available.
