# PETSc 3.25.3 for OpenHarmony

PETSc (Portable, Extensible Toolkit for Scientific Computation) 是面向科学计算的矩阵、向量和求解器库。

## 适配概要

- 版本：3.25.3
- 官网：https://petsc.org/
- 源码：https://web.cels.anl.gov/projects/petsc/download/release-snapshots/petsc-3.25.3.tar.gz
- 构建方式：PETSc Python configure + make
- 适配形态：串行静态库

## OpenHarmony 配置

本适配使用 PETSc 自带能力规避未发布外部依赖：

- `--with-mpi=0`：使用 PETSc MPIUNI 单进程 MPI 替代层
- `--with-fc=0`：禁用 Fortran 编译器
- `--download-f2cblaslapack=1`：使用 PETSc 官方外部包 f2cblaslapack
- `--with-shared-libraries=0`：生成静态库

## 验证

已通过：

- 手动 configure / make / install
- PETSc API smoke test
- `ohc-run.py conan-verify petsc 3.25.3`
- `finish` 内本地 CI 模拟 W3
