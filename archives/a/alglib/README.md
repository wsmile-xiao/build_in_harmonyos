# alglib

## Overview

ALGLIB is a C++ numerical analysis library covering linear algebra,
optimization, interpolation, statistics, integration, differential equations
and related algorithms.

## OHOS Adaptation

- Version: 4.7.0 task version, using the upstream `4.07.0` C++ GPL source
  tarball.
- Package type: C++ library.
- Build system: generated CMake project inside the Conan recipe. Upstream ships
  source files and tests, but no portable build system.
- Default build: static library with PIC.
- Dependencies: none beyond the C++ runtime and system math/thread libraries.

## Test Scope

The source tarball contains five upstream C++ test programs:

- `tests/test_i.cpp`
- `tests/test_c.cpp`
- `tests/test_x.cpp`
- `tests/test_xne.cpp`
- `tests/test_xpart0.cpp`

The recipe registers these five programs as CTest tests when the build context
can execute target binaries. `test_xne` is built with upstream's required
no-exceptions definitions in a separate object build. Conan `test_package`
builds and runs a consumer program that links `alglib::alglib` and validates
Cholesky factorization plus linear spline interpolation.

## Links

- Homepage: https://www.alglib.net/
- Source: https://www.alglib.net/translator/re/alglib-4.07.0.cpp.gpl.tgz
