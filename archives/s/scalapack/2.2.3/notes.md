# ScaLAPACK 2.2.3 Adaptation Notes

## Scope

This snapshot records the source contract and a shared-only Conan recipe bound
to the published `mpich/5.0.1.2` OHOS armv8 provider. The provider passed the
C/Fortran ABI gate. The exact r10 device snapshot completed `conan create`, all
100 registered upstream CTest entries, packaging, and the two-rank consumer.
Static output remains disabled until a host-visible Flang runtime can be
propagated to downstream consumers.

## Upstream Contract

- The top-level project enables C and Fortran.
- `find_package(MPI)` is unconditional.
- The ScaLAPACK library links `MPI::MPI_C`; the official tests also link
  `MPI::MPI_Fortran`.
- BLAS and LAPACK are both provided by `openblas/0.3.34`.
- The recipe verifies `LAPACK_FOUND` and the exact cached BLAS/LAPACK paths
  immediately after configure. This prevents upstream's fallback
  `ExternalProject` from downloading a replacement LAPACK during the build.
- BLACS sources are included under `BLACS/`; no separate BLACS package is
  required.

## ABI Contract

- OpenBLAS: LP64.
- ScaLAPACK: 4-byte Fortran `INTEGER`.
- Global Arrays: future configuration must use `--enable-i4`.
- NWChem: future configuration must keep `BLAS_SIZE=4`, `SCALAPACK_SIZE=4`,
  and `USE_64TO32=y`.

The selected MPI package must be used by ScaLAPACK, Global Arrays, and NWChem.
Mixing MPICH and Open MPI wrappers or mixing incompatible Fortran runtimes is
not allowed.

ScaLAPACK is optional for NWChem's serial eigensolver computation, but NWChem
7.3.1 still unconditionally requires an external Global Arrays package to
report either PEIGS or ScaLAPACK. This task is therefore also the no-source-patch
fallback for that configuration gate. It must not be declared a hard numerical
dependency until the downstream route is chosen: either fix the gate for
`DONTUSE_PARALLEL_LA`, or link this package into Global Arrays and validate the
complete interface.

ScaLAPACK packages Flang-built Fortran objects, so the exact
`flang-ohos/20.1.0` tool package participates in its Conan package identity via
`package_id_mode="full_mode"`. A tool recipe or binary revision must therefore
produce a distinct ScaLAPACK package ID instead of reusing an ABI-stale binary.

The current `openblas/0.3.34` recipe exports package-level `cpp_info` and does
not declare a Conan component. Conan 2.29.1 explicitly interprets
`openblas::openblas` as that package's root target; it is not a guessed
component. Keeping it explicit is necessary once the separate MPI component
is listed. The selected provider exports the exact Conan component key
`mpich::c`, which is propagated by this package.

Because the recipe is shared-only, native OHOS validation follows the existing
E077 signing contract. After the CMake build it signs every ET_EXEC/ET_DYN file
before CTest, signs the installed tree again after `cmake --install`, and signs
the independent consumer before its two-rank launch. Missing signing tools are
a hard configuration failure rather than a skipped runtime check. Each signed
temporary is accepted only when `llvm-readelf -SW` reports exactly one non-empty
`PROGBITS` `.codesign` section and the ELF header still identifies ET_EXEC or
ET_DYN before the atomic replacement.

## MPI Provider Selection

The exact published `mpich/5.0.1.2` package passed these OHOS armv8 gates:

1. `mpicc`, `mpifort` or `mpif90`, and `mpiexec` or `mpirun` exist inside the
   package.
2. C MPI, Fortran `use mpi`, Fortran `mpif.h`, and mixed C/Fortran
   `MPI_Fint` probes compile, link, and run with four-byte MPI integers.
3. The NWChem i8-core/i4-MPI bridge probe completes through the same provider.
4. Generated `MPI::MPI_C` and `MPI::MPI_Fortran` targets resolve from the
   package metadata.
5. The provider's exact Conan component key for the C MPI link interface is
   recorded together with the package reference; target names are not inferred
   from the package name.

The fresh isolated W0 resolved RREV
`6f27d84073930139fadac21a6e8b37ef`, package ID
`783062abfdc1764333d0178d0c88145bad0e32a7`, and PREV
`47c2e8a237e897a675da5e7d279cec77` from `ohpcd`, with no missing or invalid
graph nodes. The provider exports `mpich::c` and `mpich::fortran`; this recipe
uses `mpich::c` for the ScaLAPACK link interface while upstream tests discover
the Fortran target through CMake.

## Build Status

The exact r10 W3 snapshot passed on `10.62.148.108:2222` under the task-owned
root
`/storage/Users/currentUser/scalapack-2.2.3-01a00efd-20260819-r10`.

- Input: 22311 bytes, SHA-256
  `2c51a5d00154b616ae98c6b5bcce9eb857ef6378899905d0ea300efc4360d9e5`.
- Terminal: RC 0, started `2026-08-19T06:20:44Z`, finished
  `2026-08-19T07:55:58Z`, SHA-256
  `11fefe1c607de7a9430960e9c49c4741485e5bf51139964598c6d50359bc9880`.
- Build log: 9710 lines / 1083780 bytes, SHA-256
  `ef48f3c2c67f88ffd80b9cb470dd3a14556a6797c02c346d44c5c7e66fcf11ad`.
- Aggregate evidence: 7432321 bytes, SHA-256
  `ba563a6cf5a860577d3cc6caad8a69078bf7d211389ca2d53ccfc380e26851d1`.
  The local copy under
  `validation/scalapack-2.2.3/device-w3-20260819-r10/` matched the remote
  bytes and hash. Independent validation accepted 18 safe archive members,
  verified all 16 payload hashes, and re-derived the CTest, BLACS, and
  consumer cardinalities from the extracted original files.
- Upstream CTest: 100/100 passed. The suite contains 74 traditional LIN/EIG
  tests, 2 BLACS tests, 12 PBLAS correctness tests, and 12 PBLAS timing tests.
  The two longest tests were `xcheevr` at 832.97 seconds and `xzheevr` at
  840.37 seconds. `LastTest.log` SHA-256 is
  `64d7de3901c80decadaa30259d598930c04fd9558a1098714a76138db3794fe0`.
- Both BLACS outputs reached `DONE BLACS_GRIDEXIT`. Their output SHA-256 values
  are `2cf6aa20f28a9e95df149e04c84e2e5da6dd6877a7af90f2e7c416f52e547cce`
  and `e650f060ac2d79489051f3031ceb12aff2bd4dbbba791aa759b50abeed98df39`;
  the paired error-file hashes are
  `069e56fe5a4e376afd6e40970d6748360da52c9899729d43289a3d77b6191339`
  and `85f11a424a70bde369875112f8ac80fa83d68ccbe77b5df95a4db2fd286d65a4`.
- Conan created
  `scalapack/2.2.3#4cac783ec3f21720e060656fd16f310e:54349a6384308b1ece84295080a8d7090b4bb232#9e704819ec10677dc1a8636a89cc817c`.
  The signed packaged `libscalapack.so` SHA-256 is
  `a93b50883bf7bfa544d1c27e83c7cb51866f2a31b33cf110efd8df5c2005f6d7`.
- The generated `scalapack::scalapack` consumer configured and linked without
  an exported include directory, was signed, and ran through packaged
  `mpiexec -n 2`. Rank 0 reported `grid=(0,0) failures=0`; rank 1 reported
  `grid=(0,1) failures=0`. The signed consumer SHA-256 is
  `0bf91c9647a18d0f5369a28a45d53e83fa6851858b2cdd6dc6fb75e67ee458c1`.

The r8 predecessor also completed 100/100 and packaging but failed when
CMakeDeps exported Conan's default nonexistent `include/` directory. Setting
`cpp_info.includedirs = []` fixed that package contract. The r9 successor did
not enter configure because all three official GitHub source requests timed
out. No software change was made for that external network failure; r10 reused
the exact r9 input bytes and completed successfully.

Two upstream harness fixes are required for the successful result. BLACS tests
run from their original runtime directory so the `$ORIGIN` RUNPATH is retained,
and rank zero flushes `DONE BLACS_GRIDEXIT` before the intentional `MPI_Abort`.
The BLACS CMake runner also quotes `${TESTSTRING}` when appending it to a list,
preserving one empty argument instead of invoking `list(APPEND)` with invalid
arity.
