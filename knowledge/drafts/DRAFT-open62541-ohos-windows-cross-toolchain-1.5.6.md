# DRAFT: open62541 Windows host validation needs an explicit OHOS Conan toolchain

> Status: Draft | Updated: 2026-09-10
> Source event: `open62541/1.5.6` Windows local preflight

## Problem

An OHOS package can pass recipe syntax checks while never producing a valid
target package if the Windows host accidentally uses the host compiler or host
architecture. The failure is often discovered only when the consumer binary is
copied to a device.

## Adaptation Pattern

Use an explicit Conan host profile and a CMake toolchain from the DevEco
OpenHarmony Native SDK:

- host OS: `OHOS`
- host architecture: `armv8`
- target processor: `aarch64`
- CMake system name: `OHOS`
- compiler: OHOS Clang
- generator: Ninja

Keep build and host contexts separate. Use the native build profile for Conan
tools and the OHOS profile for the package being built. Do not make the
recipe depend on a personal absolute SDK path; pass the toolchain through the
profile or runner environment.

For a C library test package, `cross_building(self)` must skip execution on the
Windows host while still configuring, compiling, and linking the consumer.
Runtime execution belongs to HarmonyOS shadow CI.

## Verification

The `open62541/1.5.6` local preflight verified:

1. Conan recipe creation and package build completed.
2. The independent test package compiled and linked.
3. `llvm-readelf -h` identified the consumer as ELF64 AArch64.
4. The same consumer executed on the HarmonyOS shadow device.

This gives three separate signals: recipe correctness, target linkability,
and real-device runtime behavior.

## Do Not

- Do not run an AArch64 test binary on the Windows host.
- Do not mark a cross-compiled consumer as runtime-tested.
- Do not hardcode a developer-specific SDK directory in `conanfile.py`.
- Do not rely on the host profile to infer `os=OHOS`.
