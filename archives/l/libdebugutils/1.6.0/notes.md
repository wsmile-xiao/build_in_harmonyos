# libdebugutils 1.6.0

## Source and scope

- Upstream: Recast Navigation `v1.6.0`
- Source archive SHA-256: `d48ca0121962fa0639502c0f56c4e3ae72f98e55d88727225444f500775c0074`
- Adapted component: `DebugUtils`
- Bundled static link closure: `DetourTileCache`, `Detour`, and `Recast`
- External Conan dependencies: none
- HarmonyOS source patches: none

## Build and tests

The recipe builds the upstream CMake tree with demos/examples disabled and the Catch2 test target enabled. The upstream `Tests` executable has 30 functional cases (1 Detour and 29 Recast) plus 13 POSIX timer benchmark cases on HarmonyOS; the local OHOS x86_64 run reported all 43 passing. The Conan consumer test calls `duDebugDrawCircle` through a recording `duDebugDraw` implementation and checks the emitted primitive lifecycle and finite vertex data. A HarmonyOS-only test checks the OHOS target macro and 64-bit PC ABI. The HNP CI compiler does not consistently predefine `__MUSL__`, so the test relies on the HarmonyOS target macro; the platform toolchain provides the musl sysroot.

## Local verification

- `conan create` completed successfully with the installed HarmonyOS Native SDK 26.0.0, Clang 15.0.4, and an x86_64 HarmonyOS host profile.
- On the HarmonyOS 6.0.0.47 x86_64 VM, the upstream Catch2 executable passed all 43 cases and 804 assertions.
- The Conan consumer executable passed its DebugUtils drawing test (`duDebugDrawCircle` emitted 80 finite line vertices) and its HarmonyOS-specific OHOS/64-bit target test.
- A full Conan create on the remote HarmonyOS aarch64 device with HNP Clang 15.0.4 and CMake 4.1.2 passed: all 43 upstream cases (804 assertions) and both consumer CTest targets, including the HarmonyOS-specific target test.
- The repository Conan pre-commit L0 gate passed. It reported the existing advisory that the official GitHub source URL could use a community mirror.
- The repository W3 local-CI entry was attempted, but stopped in `setup.sh` (RC=1) because this Windows host has no `zsh`; `build_and_test.sh` therefore did not run. The CI aarch64 profile also points to the worker-only `/data/service/hnp` toolchain, while the successful local cross-build used the installed Windows HarmonyOS SDK.

For a local HarmonyOS SDK, set `OHOS_SDK_NATIVE` to the installed SDK native directory. Set `OHC_HDC_TARGET` to the attached VM target to execute cross-built test binaries through hdc.
