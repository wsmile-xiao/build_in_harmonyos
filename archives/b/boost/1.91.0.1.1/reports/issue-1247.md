# Boost 1.91.0.1.1 Multiprecision package repair

## Repair scope

The published `boost/1.91.0.1` package resolves correctly, but its selective
component closure does not install `boost/multiprecision/cpp_int.hpp` or export
`Boost::multiprecision`. Redex 2026.04.30 uses the fixed-width allocator-free
`boost::multiprecision::cpp_int_backend` contract unconditionally, so the
missing package content blocks Issue #1092.

This follow-up keeps the same official Boost 1.91.0-1 source archive and adds
Multiprecision to both the production and upstream-test component selections.
The Conan repair version is `boost/1.91.0.1.1`; it does not overwrite or reuse
the already published `boost/1.91.0.1` recipe revision.

## Package contract

- Install `include/boost/multiprecision/cpp_int.hpp`.
- Export the official `Boost::multiprecision` CMake target.
- Preserve its `headers` and compiled `random` component dependencies.
- Keep shared and static package variants valid for HarmonyOS PC AArch64.
- Do not upload artifacts from the PR validation path.

## Verification

The frozen r4 transaction completed both shared and static builds on HarmonyOS
PC AArch64. Each variant passed the complete selected upstream inventory
18/18 and all Conan consumers 7/7. Both packages contain the Multiprecision
header and CMake target, exactly 12 compiled libraries, and zero symlinks.
Shared libraries are AArch64 ELF objects with `.codesign` sections.

The candidate remains a local repair until the PR is reviewed, CI passes, the
PR is merged, the post-merge release runs, and a fresh isolated OHOS/arm64
`--build=never` lookup proves the published RREV, package IDs and PREVs.

## Relationships

- Downstream: Redex 2026.04.30, Issue #1092.
- Prior immutable dependency: `boost/1.91.0.1`.
- Source branch: `2301_80739235:fix/boost-1.91.0.1.1`.
- Publication remains a post-merge action; PR validation must not upload artifacts.
