# CLHEP 2.4.7.1 adaptation notes

## Package model

CLHEP is built with its upstream CMake project. The package exports the
upstream `CLHEP::CLHEP` CMake target and installs the CLHEP headers and library.

## Upstream validation

The recipe enables `BUILD_TESTING` and calls CTest after compilation when
`can_run(self)` is true. In cross-build jobs where the target binary cannot be
executed on the build machine, compilation remains validated and CTest is
explicitly skipped with a diagnostic message.

On OHOS, the upstream `testBug7328` case is excluded because it asserts
allocator behavior that differs on the platform. The remaining upstream CTest
suite still runs.

## Consumer validation

The test package links the installed CLHEP library set and verifies
`Hep3Vector` cross-product and magnitude results.
