# ctapi 1.1-nmu1 HarmonyOS adaptation notes

## Source and version

- Debian source version: `1.1+nmu1`.
- Conan/archive version: `1.1-nmu1`, matching the assigned task directory.
- The `+nmu1` upload is explicitly a no-source-change rebuild. The complete
  upstream payload is the public-domain `ctapi.h` interface definition.
- The recipe downloads that header from the authoritative Debian Sources
  service and verifies its SHA-256 before packaging it unchanged.

## Upstream test inventory

The source contains one header and Debian packaging metadata. It has no
`tests/` directory, test sources, build system, or registered test command.
Consequently the upstream test inventory is 0 tests and there is no upstream
test suite to modify or skip.

## HarmonyOS adaptation

No patch is required because the interface uses only `<stdint.h>`, fixed-width
integer types, and a standard C++ `extern "C"` guard. The header-only Conan
recipe has no external dependencies and produces no executable or library
binary.

The consumer suite adds three executable tests:

1. A C mock terminal exercises all three CT-API functions, APDU buffer flow,
   status codes, and terminal addresses.
2. A C++ consumer links to the C mock implementation and verifies that the
   upstream `extern "C"` declarations preserve the ABI.
3. A HarmonyOS-specific aarch64 test requires the toolchain-provided
   `__OHOS__` and `__aarch64__` macros and checks the fixed-width types used by
   every public function signature.

The test executables are linked statically and executed with the HarmonyOS
aarch64 SDK libc ABI, keeping the runtime validation independent of host
dynamic-loader paths.

## 结束

The HarmonyOS aarch64 package build, all three consumer tests, the destructive
dependency check, and the repository quality gates pass. The adaptation is
complete and ready for review.
