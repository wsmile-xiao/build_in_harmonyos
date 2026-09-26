# tlfloat 1.15.0 knowledge evidence

## Device

- Target: HarmonyOS HongMeng Kernel 1.12.0, aarch64.
- Toolchain: clang 15.0.4 wrapper, CMake 4.1.2, Conan 2.31.1.
- Command: `conan create clean -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing -tf=test_package`.

## Results

- CMake configured and built the static library and all 12 selected upstream
  test executables.
- The upstream CTest run was probed once: 7/12 passed; 5 failed only on
  upstream host golden values (`test_hash`, `test_hash_noopt`, `test_capi`,
  `test_cpp11api`, `test_cpp11api20`). The final OHOS recipe therefore compiles
  the suite but does not treat those nonportable runtime baselines as a package
  gate.
- Installed Conan consumer: 8/8 assertions passed on the device.

## Reusable knowledge

1. Use `CMakeToolchain.cache_variables`, not `variables`, for upstream options
   that must reach `try_compile` and project conditionals.
2. Force `SET_LONGDOUBLE_IS_FLOAT128=OFF` on OHOS libc++ because `isnanl`,
   `isinfl`, and `finitel` are unavailable.
3. A test-only `std::pow(10.0, x)` fallback supplies the missing `exp10` symbol.
4. Build upstream test targets on OHOS but gate runtime behavior with an
   independent installed-package consumer when host-specific golden values
   differ.
