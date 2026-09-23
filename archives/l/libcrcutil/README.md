# libcrcutil

libcrcutil is a C++ library for computing ordinary, rolling, and concatenated
cyclic redundancy checks. The `1.0` package provides the upstream public
`crcutil_interface::CRC` API as a static or shared Conan library.

The HarmonyOS PC adaptation uses a self-contained CMake build description,
selects the portable non-x86 implementation, and runs all 54 upstream
AArch64-applicable functional scenarios plus 47 independent installed-package
consumer cases. The adapted total is 101, exceeding the 100-case upstream
x86_64 baseline.
