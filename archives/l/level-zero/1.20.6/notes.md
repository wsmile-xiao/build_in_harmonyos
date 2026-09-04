# Level-Zero 1.20.6 HarmonyOS PC notes

## Scope

- Upstream tag `v1.20.6` from https://github.com/oneapi-src/level-zero
- SHA256: `3fac6c9efcb013e81c751159e8312302371658ed149e3a1a1a7a80cceea48ce9`
- The package installs the Level Zero loader library (`libze_loader.so`)
  and companion layers (`libze_validation_layer.so`, `libze_tracing_layer.so`),
  plus public headers under `include/level_zero/`.

## Build System

CMake (not autotools). The upstream project uses a standard CMake build.

## Patch: dlinfo() guard

The `dlinfo()` function is a glibc-specific extension not available on
OHOS libc. The patch `0001-guard-dlinfo-with-glibc.patch` changes
`#ifndef _WIN32` to `#if !defined(_WIN32) && defined(__GLIBC__)` in
`source/loader/ze_loader.cpp`. This guards the `dlinfo()` call which
is only used in debug trace mode to print the driver library path.
No functional impact.

The patch uses `__GLIBC__` (standard libc detection macro, NOT a
platform macro like `__OHOS__`). This is acceptable under R8.

## Dependencies

No external conan dependencies. The only system libraries needed are
`dl` and `pthread`, both provided by the OHOS system.

## Build Configuration

CMake options used:
- `-DBUILD_L0_LOADER_TESTS=OFF` — skip building upstream tests
- `-DSYSTEM_SPDLOG=OFF` — use bundled spdlog, no system dependency
- `-DINSTALL_NULL_DRIVER=OFF` — no null driver (driverless system)

## Test

The test package calls `zelLoaderGetVersions` and `zeInit` APIs.
On driverless systems, `zelLoaderGetVersions` returns 0 (success)
with 1 component (the loader itself), and `zeInit` returns an error
code (expected on driverless systems). The test passes as long as
the API is callable and the binary is correctly linked and signed.

## Validation

- conan-verify passed all 8 gates (G0-G4, L2/L4/L5)
- conan create completed successfully with exit code 0
- Test binary signed with binary-sign-tool and executed successfully
- Package contains: libze_loader.so, libze_validation_layer.so,
  libze_tracing_layer.so, and level_zero headers
- License: MIT

---

**编译结束**: 2026-09-04 06:40
**最终状态**: published
