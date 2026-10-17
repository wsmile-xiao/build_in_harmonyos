# PETSc (complex-scalar variant)

PETSc 复数标量变体 —— 一个以 `--with-scalar-type=complex` 构建的 PETSc，用于求解复数
线性/非线性方程组（电磁场、频域声学、量子力学等）。

## 功能概述

- 与上游 PETSc 完全相同的 API 与功能：向量、矩阵、Krylov 子空间（KSP）、预条件子（PC）、
  非线性求解器（SNES）、时间积分器（TS）
- `PetscScalar` 为 C99 `double _Complex`（宽度为 `PetscReal` 的 2 倍），
  `PETSC_USE_COMPLEX` 已打开
- 顺序（serial）构建：`--with-mpi=0`（MPIUNI），无需 MPI 运行时
- 自带 BLAS/LAPACK：`--download-f2cblaslapack=1`，复数例程（`zgemm`/`zdotc`/`zheev`）
  已包含，不需要外部 OpenBLAS/MKL

## OHOS 适配

- 走 PETSc 自己的 Python `configure`，不是 autotools 流程；CI 的通用
  clean-verify 流程不适用
- `--with-fc=0`：OHOS 侧没有 Fortran 编译器，Fortran 接口整体关闭
- `--with-mpi=0`：避开尚未发布到制品仓的 MPI 依赖，得到 MPIUNI 串行库
- `--with-scalar-type=complex` 会改变 ABI（`PetscScalar` 宽度翻倍、
  `petscconf.h` 重写），因此独立成包，而不是 `petsc` 的一个 option ——
  否则同一个 Conan 图里同时需要实数和复数 PETSc 的两个下游无法共存
- 消费方不需要额外 `-D PETSC_USE_COMPLEX`：该宏已在安装出的 `petscconf.h` 中，
  `petscsys.h` 会包含它

已知问题：

- 不提供 Fortran 绑定（与同族 `petsc/3.25.x` 一致）
- 仅提供 double 精度；其他精度请另建包名，不要在本包加 option

## 依赖关系

- 编译依赖：无（self-contained；BLAS/LAPACK 由 `--download-f2cblaslapack=1` 提供）
- 运行依赖（OHOS/Linux）：`m`、`stdc++`

## 参考资料

- 官网：<https://petsc.org/>
- 源码：<https://gitlab.com/petsc/petsc>
- 复数标量说明：<https://petsc.org/release/manualpages/Sys/PetscScalar/>
