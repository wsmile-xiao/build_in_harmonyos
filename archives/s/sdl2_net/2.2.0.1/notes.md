# SDL2_net 2.2.0.1

## Scope

This revision creates a new Conan package identity for SDL2_net 2.2.0 whose
only SDL provider is the published sdl2/2.32.10 package. The suffix is required
because the merged 2.2.0 recipe already represents the incompatible
sdl2/2.30.10 closure. The old Issue #1349 and PR #3164 remain immutable
historical records and are not reused as current validation.

The recipe keeps the upstream CMake build and the existing shared/static
component contract. The package requires transitive SDL2 headers and libraries,
and it binds the SDL2 package's installed native CMake configuration before
generating the build toolchain. Both SDL2Config.cmake (the published standard
name) and the historical lowercase spelling are recognized; no configuration
file is generated or copied into the dependency package.

The OHOS shared-library portability patch is keyed by the exact recipe version
`2.2.0.1` in `conandata.yml`. Conan's `apply_conandata_patches()` performs an
exact version lookup, so a revision-style key such as `2.2.0-r1` silently
skips the patch for this successor. The version-key binding is checked before
any shared-package build; the static package remains governed by the same
source and dependency identity.

## Toolchain boundary

Windows Conan execution is split into a Windows build profile and an OHOS
aarch64 host profile. The host profile points to the read-only DevEco LLVM
installation and loads its official ohos.toolchain.cmake. That toolchain sets
the aarch64-linux-ohos compiler target, SDK sysroot, lld linker, llvm-ar, and
OHOS platform rules. Parallel build jobs are limited to two. The SDK is never
modified and generated build output belongs to the task-local F-drive Conan
home.

## Consumer accounting

The upstream installed CMake consumer is one independent logical entry. The
adapted test package contains six independent network consumers: strict
initialization/version/byte-order conversion, packet boundary lifecycle,
address-resolution error handling, UDP loopback, bidirectional TCP loopback,
and socket-set readiness/cleanup. Shared and static package modes exercise the
same seven inputs twice for package-mode coverage but do not double the logical
denominator. Loopback traffic is restricted to 127.0.0.1; no external service
or port reachability is used as a substitute for API assertions.

The target-runtime result remains NOT_RUN until a signed package is consumed by
the authorized OpenHarmony device transaction. Local cross compile and host
loopback execution, when present, are recorded separately from target
execution and from Conan remote publication.

## Current local evidence

The SDL2_net static package was created locally with Conan 2.29.1 using the
published sdl2/2.32.10 static package. The recipe revision is
ff7ca722767e5c938fdc22724a2f947b, the package ID is
7b8a00ecd1dcc9231ac0df36c334f8d078a74783, and the local package revision is
8d0c2c006a3cf03f4828e4c0c14f1e87. The build used the SDK's official OHOS
toolchain and installed libSDL2_net.a, SDL_net.h, and SDL2_net CMake metadata.
The static test package then compiled and linked all seven independent network
consumers (one upstream installed CMake consumer plus six adapted consumers).
This is local compile/install evidence only; it is not a release-remote
binary, target execution, or DOSBox W3 result.

The exact 8,707,169-byte official source archive used by the local build has
SHA-256 4e4a891988316271974ff4e9585ed1ef729a123d22c08bd473129179dc857feb.
The Conan create log SHA-256 is
bf44d6850c55f54d6c8117b603d533092b355edb33fd7f4d9ac2953a54536e23, and the
installed libSDL2_net.a SHA-256 is
6448ed46eeab766d3b0076ea98e7ee3371219814d34a3f8a177805704329448f.

An earlier invocation failed before build because Conan 2.29.1 does not
accept the --non-interactive option. A second invocation failed because
core.* configuration cannot be supplied in a profile. The successful retry
uses the version's normal non-interactive behavior. These command-line
compatibility failures do not alter source or package bytes.

## Release gate

Before creating the SDL2_net PR, the PRE_CREATE contract must bind the new
Issue #2490, current HEAD/tree, the complete consumer inventory, and the
required knowledge draft pair. After PR creation, POST_CREATE must be read
back before AI Review, CI, or release. CI must build the exact 2.2.0.1
recipe and publish the OHOS binary through the formal release job. A fresh
Conan home must then resolve sdl2_net/2.2.0.1 and sdl2/2.32.10 with
conan install --build=never; a local fallback package is never uploaded or
treated as a remote publication.

## Safety boundaries

Do not mutate the historical 2.2.0 recipe, old package identity, Issue #1349,
PR #3164, or their device evidence. Do not claim target runtime, native SDL2
video/audio capability, CI success, or remote availability from this local
package. If the release job cannot publish a binary that the fresh Conan home
can parse, keep the dependency blocked and do not advance DOSBox CI.
