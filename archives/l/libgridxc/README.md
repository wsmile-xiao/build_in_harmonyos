# libGridXC

libGridXC computes exchange-correlation energies and potentials on radial and 3D grids for density-functional calculations. It started as SiestaXC inside SIESTA.

## OHOS adaptation

- **Build system**: CMake Fortran build, serial only.
- **Fortran toolchain**: `flang-ohos/20.1.0` provides the device Fortran compiler.
- **Options**: `WITH_MPI=OFF`, `WITH_LIBXC=OFF`, `WITH_GRID_SP=OFF`.
- **Tests**: upstream ctest `test1`, `test2`, `test3`, `test4`, `test6` run serially.

## Dependencies

- Build requires `flang-ohos/20.1.0`.
- No runtime library dependencies besides the Fortran runtime packaged with the recipe.

## References

- Upstream: https://gitlab.com/siesta-project/libraries/libgridxc
- Docs: https://siesta-project.github.io/gridxc-docs/
