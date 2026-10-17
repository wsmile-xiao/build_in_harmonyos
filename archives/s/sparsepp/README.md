# sparsepp

Sparsepp 1.23 is a fast, memory-efficient C++ hash table library. It is a
header-only BSD-3-Clause package and requires C++11 or newer.

## OpenHarmony package

- Target: HarmonyOS PC AArch64 with Clang and libc++
- Build system: Conan 2 with the upstream `tests/makefile` entry point
- Dependencies: none beyond the C++ standard library
- CMake target: `sparsepp::sparsepp`
- Package contents: the public `sparsepp/` headers and the upstream license

The recipe runs the upstream default test build and `make test`; the Conan
consumer test separately verifies the installed header package.
