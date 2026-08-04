# libformfactor 0.4.0

- Builds the C++20 library and all 18 upstream CTest executables.
- Executes all 18 upstream CTest cases during the Conan build with
  `CTEST_OUTPUT_ON_FAILURE=1` and `CTEST_PARALLEL_LEVEL=1`; the build fails if
  any upstream test does not pass.
- Bundles LibHeinz 4.0.0 because it is header-only and is part of
  libformfactor's public API.
- The consumer validates construction and a finite form-factor calculation.
- OHPCD CI #11780 passed: 18/18 upstream CTest programs and the 3 consumer
  assertions are executed as release gates.
