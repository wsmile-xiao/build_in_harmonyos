# SuperNOVAS

SuperNOVAS is a C/C++ astrometry library derived from NOVAS. This archive packages version 1.7.1 for OpenHarmony PC through Conan 2.

## Package contents

- Static C library `libsupernovas`
- Static C++ wrapper library `libsupernovas++`
- Public headers `novas.h` and `supernovas.h`
- Upstream CMake package metadata

## OpenHarmony adaptation

- Build with CMake using static libraries.
- Disable curl, online tests, optional ephemeris plugins, examples, benchmarks, and documentation.
- Enable the C++ wrapper target so both C and C++ public APIs are packaged.
- Add a Conan `test_package` that compiles and runs deterministic C and C++ public API consumers.
