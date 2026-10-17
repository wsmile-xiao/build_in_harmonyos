# CMake library installs need an explicit public-header and macro audit

## Symptom

A CMake library target compiles and links in its own build, but a Conan
consumer cannot include the public API or the API symbols are not declared.
The package can appear healthy if validation only checks that a library file
exists.

## Root cause

Upstream CMake `install(TARGETS ...)` rules do not necessarily install public
headers.  In addition, some libraries conditionally declare their exported C
or C++ API behind a compile definition that is enabled while building the
library but is not automatically present for consumers.  The binary target
can therefore be valid while the generated package metadata is incomplete.

## Fix

1. Read the upstream install rules and public header guards before choosing the
   Conan package type and `package_info` values.
2. Stage only the verified public headers into `package_folder/include` when
   the upstream install step omits them.
3. Export any required public compile definition through `cpp_info.defines`,
   and let generated `CMakeDeps` metadata carry it to consumers.
4. Build a separate consumer with `CMakeDeps`/`CMakeToolchain`, link the
   generated target, call a real API path, and execute it when the target can
   run.

## Validation

For AStyle 3.6.18, the upstream CMake install produced the `astyle` library
but no headers.  The recipe staged `astyle.h` and `astyle_main.h` and exported
`ASTYLE_LIB`.  A native Linux consumer linked the resulting static library,
called `AStyleMain` and `AStyleGetVersion`, and exited successfully.  The
upstream CLI regression suite separately passed all 16 style directories.

## Applicability and safety boundaries

This applies to C/C++ packages whose CMake install surface is narrower than
their public source surface or whose headers contain producer/consumer API
guards.  Do not copy all source headers, infer public status from filenames,
or replace a linked API test with a version string or file-presence check.
Native execution does not prove OHOS target execution; the target architecture
still needs its own build and device/CI validation.
