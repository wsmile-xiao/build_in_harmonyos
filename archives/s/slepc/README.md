# SLEPc 3.25.1 for OpenHarmony

SLEPc 是构建在 PETSc 之上的大规模特征值问题、奇异值分解和相关谱计算库。

## 适配概要

- 版本：3.25.1
- 官网：https://slepc.upv.es/
- 源码：https://slepc.upv.es/download/distrib/slepc-3.25.1.tar.gz
- 依赖：`petsc/3.25.3`
- 构建方式：SLEPc/PETSc Python configure + make
- 适配形态：串行静态库，使用 PETSc MPIUNI

## 验证

适配包含上游 EPS 测试和 Conan 消费者测试。消费者测试创建 2x2 对角矩阵，通过 SLEPc EPS 求解主特征值，并验证收敛、特征值与误差。
