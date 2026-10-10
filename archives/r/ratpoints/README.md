# ratpoints

ratpoints is a library and command-line program for finding rational points on hyperelliptic curves. It implements an optimized quadratic sieve and is distributed under GPL-2.0-or-later.

## OpenHarmony PC adaptation

The Conan recipe builds the upstream 2.1.3 C sources with the native HarmonyOS Clang toolchain and the published `gmp/6.3.0.1` package. It produces the `ratpoints` library and command-line program. The original Makefile places system libraries before the static `ratpoints` archive, which fails with modern linkers; the recipe uses the correct object and library ordering without modifying upstream source files.

The recipe executes the complete upstream `rptest` regression program and compares all 1000 generated curve-result lines byte-for-byte with the official `testbase`. The package consumer tests exercise the public C API, the installed CLI, and HarmonyOS arm64 ABI assumptions used by the implementation.

Upstream project: https://www.mathe2.uni-bayreuth.de/stoll/programs/
