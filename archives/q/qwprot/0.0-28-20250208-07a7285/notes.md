# qwprot 0.0-28-20250208-07a7285 adaptation notes

## Build environment

- Build system: header-only Conan package
- Build date: 2026-09-27
- Compiler: HarmonyOS clang/clang++ 15, aarch64
- Status: built

## Source and packaging

1. The source is pinned to upstream commit
   `07a728526ebddb93804bb34d295872cc0e8128b7`.
2. The upstream revision contains one public header and no build system.
3. `src/protocol.h` is installed as `include/qwprot/protocol.h`.
4. The license notice embedded in `protocol.h` is retained in the installed
   header and copied to `licenses/protocol.h`.
5. No source patches or third-party dependencies are required.

## Language preflight boundary review

The generic language detector reports `other` because it deliberately treats
`.h` as language-neutral and this upstream revision has no `.c` or `.cpp`
translation unit. Manual review under the documented header-only boundary rule
confirms C/C++ compatibility: the complete archive contains `src/protocol.h`,
the public header declares the protocol C structs and constants, and both the
HarmonyOS C++17 compiler probe and packaged C++ consumers compile successfully.
The task therefore remains in the C/C++ compatible family.

## Tests

- Upstream test programs: 0 (the complete upstream archive contains no test
  directory, test source, or test command).
- Portable consumer test: 15/15 checks passed.
- HarmonyOS aarch64 consumer test: 12/12 checks passed.
- Added test programs: 2/2 passed (27/27 checks, 100%).

The tests consume the generated CMake target `qwprot::qwprot` and validate
protocol constants, extension masks, public structures, consumer-provided
types, HarmonyOS compiler macros, aarch64 data-model assumptions, and network
structure layout.
