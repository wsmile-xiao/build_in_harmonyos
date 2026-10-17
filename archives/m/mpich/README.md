# MPICH

MPICH is a portable implementation of the Message Passing Interface standard.
The OpenHarmony PC archive uses the local `ch3:sock` transport. The 5.0.1 C
package uses the minimal `gforker` process manager.

`mpich/5.0.1.2` adds the `mpif.h` and `use mpi` interfaces built with
`flang-ohos/20.1.0` and uses Hydra for the complete upstream process-manager
contract. It exports distinct Conan component keys `c` and
`fortran`, with generated CMake targets `MPI::MPI_C` and
`MPI::MPI_Fortran`. The package carries the matching static Flang runtime
archives and uses package-relative compiler wrappers.

The package does not claim `mpi_f08`: the selected Flang package and matching
OHOS SDK do not provide the required `ISO_Fortran_binding.h` compiler header.

- Homepage: https://www.mpich.org/
- Source: https://github.com/pmodels/mpich/releases/tag/v5.0.1
- License: `mpich2`; version 5.0.1.2 additionally redistributes LLVM Flang
  runtime archives under `Apache-2.0 WITH LLVM-exception`, so its complete
  expression is `mpich2 AND (Apache-2.0 WITH LLVM-exception)`.

Fortran consumers must use `flang-ohos/20.1.0` and select the exact
`mpich::fortran` component. MPI integer handles and counts remain four bytes;
BLAS and LAPACK integer configuration is a separate downstream decision.
