# PHAT

PHAT (Persistent Homology Algorithm Toolbox) is a C++ header library and command-line utility for computing persistence pairs by boundary-matrix reduction.

## Features

- Multiple boundary-matrix representations.
- Standard, twist, chunk, row, spectral-sequence, swap, exhaustive, and retrospective reductions.
- Primal and dual persistence-pair computation.
- ASCII and binary matrix input through the `phat` utility.

## HarmonyOS adaptation

The C++11 headers and the `phat` utility build with the HarmonyOS Clang toolchain. OpenMP is an optional upstream optimization; the package uses PHAT's upstream sequential fallback so no unavailable OpenMP runtime is introduced.

## Dependencies

PHAT has no third-party build or runtime dependencies for its C++ interface.

## References

- Upstream repository: https://bitbucket.org/phat-code/phat
- Version 1.7 source: https://bitbucket.org/phat-code/phat/get/v1.7.tar.gz
