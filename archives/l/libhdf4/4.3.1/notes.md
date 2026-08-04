# HDF4 4.3.1

- Builds the static `hdf` and `mfhdf` libraries with required JPEG and zlib
  support.
- Keeps the upstream C library test suites enabled and requires the complete
  registered CTest inventory to run during the Conan build.
- Fortran, Java, tools, examples, and optional SZIP are disabled to keep the
  OHOS package focused and reproducible.
- The consumer writes and reads a real Scientific Data Set and verifies every
  integer value.
- Upstream CTest pass rate is gated by the Conan build: all 68 registered
  upstream tests must pass, otherwise CI fails.
