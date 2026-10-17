# gflags for HarmonyOS PC

gflags provides command-line flag declaration, parsing, validation and help
generation for C++ applications. The `2.2.2` archive is packaged as a shared
library for HarmonyOS PC AArch64.

## Package

| Field | Value |
|---|---|
| Version | 2.2.2 |
| Upstream | https://github.com/gflags/gflags |
| Build system | CMake |
| Conan reference | `gflags/2.2.2` |
| Output | `libgflags.so`, headers, CMake config and pkg-config metadata |

The package builds only the threaded gflags library. The optional no-threads
variant and the shell-completion helper are excluded to keep the package API
and command surface unambiguous.

## Verification

The DevEco OHOS Clang 15.0.4 cross-build produces ELF64 AArch64 output. All
five upstream test executables compile, and CTest discovers 51 tests. Local
Windows cannot execute those target binaries, so actual upstream-test and
consumer-test execution remains a native HarmonyOS CI requirement.

See `2.2.2/notes.md` for the exact verification boundary.
