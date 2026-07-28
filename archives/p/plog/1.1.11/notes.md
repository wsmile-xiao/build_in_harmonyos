# plog 1.1.11 adaptation notes

## Source

- Canonical release: `https://github.com/SergiusTheBest/plog/tree/1.1.11`
- Archive SHA-256:
  `d60b8b35f56c7c852b7f00f58cbe9c1c2e9e59566c5b200512d0cdbb6309a7c2`
- License: MIT
- Runtime dependencies: none

## Build

`plog` is header-only. The recipe still configures and builds the upstream
CTest matrix so the public headers are compiled in the default mode, wchar
mode, and every compiler-supported C++ standard from C++11 through C++23.

The upstream test project enables only C++, but its `CheckTypeSize` invocation
defaults to a C probe with newer CMake versions. The included patch selects the
C++ probe explicitly without changing test behavior.

## Test inventory

The exact 1.1.11 release registers eight CTest entries with the OHOS Clang
feature set:

1. `PlogTest`
2. `PlogTest_wchar`
3. `PlogTest_cxx_std_11`
4. `PlogTest_cxx_std_14`
5. `PlogTest_cxx_std_17`
6. `PlogTest_cxx_std_20`
7. `PlogTest_cxx_std_23`
8. `PlogTest_cxx_std_23_wchar`

Both the native GCC and OHOS Clang validations expose 88 doctest cases and 570
assertions across those entries. All eight generated test executables are run.

The separate Conan consumer test has nine assertions across a normal logging
scenario and an invalid-severity fault-injection scenario.

## Verification

- Native Conan create: all 8 CTest entries passed; 88 doctest cases and 570
  assertions passed, with 0 failures and 0 skips.
- OHOS aarch64: the recipe, all 8 upstream test executables, and the consumer
  test compiled and linked with DevEco Clang 15. `llvm-readelf` identified the
  generated executables as AArch64 ELF64.
- HarmonyOS PC emulator: HarmonyOS 6.1.0 (API 23), x86_64. All 8 upstream
  executables exited 0; 88 doctest cases and 570 assertions passed, with 0
  failures and 0 skips.
- Emulator consumer checks: the normal scenario and the
  `--invalid-severity` fault-injection scenario both exited 0.
