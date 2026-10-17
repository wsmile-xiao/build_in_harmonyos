# PBC

PBC (Pairing-Based Cryptography) is a C library that provides low-level
operations for pairing-based cryptosystems, including cyclic groups,
bilinear pairings, and suitable curve generation.

## OHOS adaptation

- Builds the official 1.0.0 release with Autotools and Clang.
- Supports both shared and static Conan packages without changing the public API.
- Adapts the release `config.guess` and `config.sub` scripts for HarmonyOS.
- Runs all 134 upstream test cases plus an installed-package consumer test.

## Dependencies

- `gmp/6.3.0` is the public library dependency.
- `flex/2.6.4.2` and `bison/3.8.2` are build tools.

## References

- https://crypto.stanford.edu/pbc/
- https://crypto.stanford.edu/pbc/download.html
