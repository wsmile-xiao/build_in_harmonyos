# BLAS

Netlib 参考 BLAS（Basic Linear Algebra Subprograms）：线性代数基础运算标准库
（level 1/2/3 向量与矩阵运算），3.12.1 版本随 LAPACK 3.12.1 官方发行。

## 依赖

- 构建期：`flang-ohos/20.1.0`（tool_requires，鸿蒙无 gfortran）
- 运行期：无（静态库）

## OHOS 适配要点

- 纯 Fortran 77 源码，走上游 make 路径（`BLAS/Makefile` → SRC 产 `libblas.a`）
- 绕开 CMake：顶层 CMake 的 BLAS 目标需 Fortran 链接探针，flang-ohos 精简运行集无法完成
- `make.inc` 变量集在 conanfile.py `generate()` 写入：`FC`（flang + target/sysroot/resource-dir）、`FFLAGS`、`LDFLAGS`（Fortran 运行时）、`AR/RANLIB`（llvm-ar/llvm-ranlib）、`BLASLIB`（build_folder）
- 消费方以 C 直接调用 Fortran LP64 符号（`ddot_`/`dgemm_` 等尾下划线约定），链接 `-lblas -lFortranRuntime -lFortranDecimal -lm`
- 上游测试：`BLAS/TESTING` 12 个 blat 驱动（level1/2/3 × s/d/c/z），`make run` 全部真实运行

## 版本

| 版本 | 状态 | 构建日期 | 备注 |
|------|------|---------|------|
| 3.12.1 | built | 2026-09-15 | 零补丁；上游测试 12 驱动全部通过 |
