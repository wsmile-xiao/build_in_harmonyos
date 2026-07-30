# libxxhash (xxHash)

XXHash is an Extremely fast Hash algorithm, running at RAM speed limits. It successfully completes the SMHasher test suite which evaluates collision, dispersion and randomness qualities of hash functions.

## Features

- Extremely fast
- Simple to use
- Portable across all platforms
- Zero dependencies

## Build System

CMake-based build system (cmake_unofficial/). Simple to compile with minimal configuration.

## Dependencies

None. Zero dependencies.

## Notes

- Small library with simple build process
- Supports both static and shared library builds
- CMake build works on HarmonyOS without patches
- xxhsum CLI tool available in upstream but disabled in this recipe
