# ScaLAPACK

ScaLAPACK is a distributed-memory dense linear algebra library built on
BLAS, LAPACK, BLACS, and MPI.

## Features

- Parallel linear systems, eigensolvers, singular value decomposition, and
  matrix factorizations.
- C BLACS entry points and Fortran ScaLAPACK/PBLAS routines.
- Upstream MPI test suites for linear algebra and eigenvalue routines.

## OpenHarmony Adaptation

- The package must use one published MPI implementation that provides both C
  and Fortran wrappers compiled for the same ABI as `flang-ohos/20.1.0`.
- BLAS and LAPACK are supplied by `openblas/0.3.34` in LP64 mode.
- ScaLAPACK's integer ABI remains 32-bit (`INTEGER=4`) for compatibility with
  Global Arrays and NWChem.
- BLACS is built from the ScaLAPACK source tree; it is not a separate package.
- NWChem's serial eigensolver path does not computationally require ScaLAPACK,
  but the unmodified v7.3.1 external-GA gate still requires GA to advertise
  ScaLAPACK or PEIGS. This package is retained as the no-source-patch fallback
  until the downstream integration route is chosen.

The 2.2.3 adaptation uses the published `mpich/5.0.1.2` OHOS armv8 package.
Its C/Fortran wrappers, integer ABI, generated CMake targets, and Conan
component keys passed the dependency W0 gate. The exact OHOS armv8 W3 snapshot
then passed all 100 upstream CTest entries and a signed two-rank
`scalapack::scalapack` consumer. ScaLAPACK installs no public headers, so the
Conan target intentionally exports an empty include-directory list.

## Dependencies

- `openblas/0.3.34`
- `flang-ohos/20.1.0` (build tool)
- `mpich/5.0.1.2`

## References

- https://github.com/Reference-ScaLAPACK/scalapack
- https://www.netlib.org/scalapack/
