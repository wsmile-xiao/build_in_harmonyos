# SLEPc 3.25.1 适配笔记

## 编译环境

- 构建系统：SLEPc/PETSc Python configure + GNU make
- 编译日期：2026-07-21
- 编译器：Clang 15
- 状态：built

## 编译步骤

SLEPc 依赖已发布的 `petsc/3.25.3`。探索阶段将 Conan PETSc 包复制到临时目录并重定位其配置元数据，然后执行：

```bash
SLEPC_DIR=$PWD PETSC_DIR=/storage/Users/currentUser/tmp/slepc-petsc-3.25.3 \
  ./configure --prefix=/storage/Users/currentUser/tmp/test-install-slepc-3.25.1 \
  --with-slepc4py=0
SLEPC_DIR=$PWD PETSC_DIR=/storage/Users/currentUser/tmp/slepc-petsc-3.25.3 make -j1
SLEPC_DIR=$PWD PETSC_DIR=/storage/Users/currentUser/tmp/slepc-petsc-3.25.3 make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | SLEPc configure 无法链接 PETSc | PETSc 安装元数据保留了 Conan 构建目录的绝对前缀，该目录在下载二进制包后不存在 | 配方将 PETSc 包复制到 `build_folder/petsc`，并仅在私有副本中重定位文本配置文件 |
| 2 | 构建阶段调用不存在的 `/data/service/hnp/bin/python3` | PETSc 配置记录了发布 worker 的 Python 绝对路径 | 私有副本中将该路径替换为当前 `sys.executable` |
| 3 | `make -j2` 报 jobserver FIFO 不支持 | 当前 OpenHarmony 文件系统不支持 GNU make jobserver FIFO | Conan 配方固定使用 `make -j1` |
| 4 | 初次 `make check` 缺少 MPIUNI launcher | PETSc Conan 包未安装生成阶段的 `petsc-mpiexec.uni` 脚本 | 单进程上游 `test10` 可直接运行；消费者测试使用 `PETSC_COMM_SELF`，不依赖 launcher |

## 依赖版本

- `petsc/3.25.3`：串行静态 PETSc，MPIUNI，f2cblaslapack

## 验证结果

探索构建、安装和上游 `make check` 均通过。随后执行完整 `make test`：上游 186 个测试源文件在当前串行 PETSc MPIUNI 配置下生成 665 个参数化目标，共产生 2010 个 TAP 检查，其中 1966 通过、0 失败、44 按上游能力条件跳过。覆盖 SYS、EPS、SVD、PEP、NEP、MFN、LME 全部模块。消费者测试另行创建 2x2 对角矩阵，调用 SLEPc EPS API，并检查收敛数、主特征值和相对误差。

## 注意事项

- 当前适配为串行静态库，与 PETSc 3.25.3 的 MPIUNI 配置一致。
- 未启用 `slepc4py`、ARPACK、PRIMME 等可选组件。
- 不修改依赖的 Conan 缓存；PETSc 元数据重定位仅发生于 SLEPc 私有构建目录。
- PETSc 制品未安装 `petsc-mpiexec.uni` 与 `petscdiff` 测试工具；完整回归通过环境变量使用 PETSc v3.25.3 官方脚本副本，仅作用于 SLEPc 私有测试工作区。
- 44 个 SKIP 为上游根据当前 MPIUNI、无 Fortran/CUDA/HIP/外部求解器配置做出的条件跳过，不计为失败。
---

**编译结束**: 2026-07-21 09:30
**最终状态**: built
