# hypre 3.1.0

- Builds a static sequential CPU library with internal BLAS and LAPACK.
- Compiles the upstream IJ, Struct, and SStruct solver test groups.
- Runs the three registered upstream CTest groups when the built target is
  runnable; non-runnable cross-build configurations warn and skip upstream
  CTest so the compiled package can still be created.
- The consumer verifies initialization, the exact 3.1.0 version tuple, and
  finalization.
- Upstream CTest pass rate is gated by the Conan build when tests can run:
  all 3 registered upstream groups must pass, otherwise CI fails.
