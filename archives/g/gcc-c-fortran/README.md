# GCC C/Fortran

GNU Compiler Collection 9.5.0 providing C (`gcc`) and Fortran (`gfortran`)
compilers for HarmonyOS PC (AArch64). Includes the `libgfortran` runtime
library for Fortran intrinsics, formatted I/O and formatted output.

## 已编译版本

- `9.5.0`：`built`（本地构建验证通过，官方 CI 待运行）

## OHOS 适配要点

- Native OHOS/AArch64 build uses the same in-tree source transforms as the
  C-only `gcc/9.5.0` package (OHOS musl target mapping, config.sub patching,
  HMDFS umask relaxation).
- Fortran frontend `f951` is built alongside `cc1` as part of `make all-gcc`.
- `libgfortran` (Fortran runtime) is built as a separate target library after
  `libgcc`, with both using the signed `xgcc-sign` wrapper for target compilation.
- `libquadmath` and `libgomp` are disabled to match the minimal `gcc/9.5.0`
  baseline; gfortran provides full REAL(4)/REAL(8) IEEE support without
  quad precision (REAL(16)) and without OpenMP.
- The installed package provides relocatable `gcc` and `gfortran` shell
  wrappers that inject the correct sysroot, include and library search paths.

## 参考

- [GCC Fortran](https://gcc.gnu.org/fortran/)
- [GCC 9.5.0 源码](https://ftp.gnu.org/gnu/gcc/gcc-9.5.0/)
