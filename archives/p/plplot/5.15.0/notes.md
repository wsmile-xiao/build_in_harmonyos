# plplot 5.15.0 OpenHarmony adaptation

- Source: official PLplot 5.15.0 SourceForge release archive.
- Build system: CMake.
- W0 result: the selected core C/C++ configuration has no required Conan
  dependencies. Optional language bindings and GUI/file backends are disabled.
- Enabled scope: C core library, C++ binding, PostScript file devices (`ps`,
  `psc`) for upstream example tests.
- Disabled scope: dynamic drivers, Java/Python/Lua/Tcl/Fortran/Ada/OCaml/D
  bindings, Qhull/CSA, FreeType and GUI-oriented drivers.

## Upstream tests

`BUILD_TEST=ON` is enabled and the recipe runs two upstream CTest cases when
the target can execute:

- `examples_c`
- `examples_cxx`

Both tests use PLplot's upstream example-test driver with the `psc` file
device. `TEST_DIFF=OFF` avoids depending on extra image-diff tooling while
still executing the upstream C and C++ plotting examples.

## Consumer test

The test package builds a C++ consumer, links the packaged PLplot libraries,
checks the C API version string, constructs the C++ `plstream` wrapper, and
checks the C++ wrapper version string.
