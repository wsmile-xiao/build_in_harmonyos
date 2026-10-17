# tiny-aes-c 0.4.2 knowledge evidence

## Device

- Target: HarmonyOS HongMeng Kernel 1.12.0, aarch64.
- Toolchain: clang 15.0.4 wrapper, CMake 4.1.2, Conan 2.31.1.
- Command: `conan create clean -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing -tf=test_package`.

## Results

- The pinned upstream archive was audited and contains no test source, test
  directory, or build/test command; upstream inventory is 0.
- The recipe applied the portability patch, compiled `aes.cpp` as C++17, and
  packaged the static archive and public header.
- The installed consumer linked through `tiny-aes-c::tiny-aes-c` and passed
  all 12 assertions on the real HarmonyOS target.
- The target clang wrapper injects linker-only flags into compile commands. The
  recipe and consumer demote only `unused-command-line-argument`; source
  warnings remain fatal under `-Werror`.

## Reusable knowledge

1. For a source-only C++ archive, obtain `cpp` and `ar` from the Conan profile
   rather than relying on host executable names.
2. Include the standard header required by the implementation and replace
   inactive union-member reads with explicit byte mapping.
3. Return before pointer arithmetic for an empty vector API.
