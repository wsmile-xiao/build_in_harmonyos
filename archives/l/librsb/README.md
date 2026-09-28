# librsb

## 简介
librsb 是一个共享内存并行的 Sparse BLAS 库，实现 Recursive Sparse Blocks (RSB)
稀疏矩阵格式的矩阵运算（SpMV、三角求解、矩阵 I/O 等），由 Michele Martone 维护。

## OHOS 适配
- 构建系统为 autotools；config.guess 无法识别 HarmonyOS，需显式传递
  `--build=aarch64-unknown-linux-gnu`
- OHOS 无 Fortran 编译器（gfortran），configure 自动降级（HAVE_FC=false）：
  Fortran 接口（rsb_blas_sparse.F90）与 Fortran 示例自动跳过，C/C++ 功能完整
- 上游 `make check` 为空目标（全树无 TESTS/check_PROGRAMS）；真实可运行套件是
  `examples/` 的 `tests` 目标（bench.sh + 9 个示例二进制 + autotune 实矩阵运行）
- `rsb_gtests.cpp` 的 221 个 gtest 用例需系统 GTest，OHOS 环境无法运行（见补充说明）
- 依赖制品仓 `zlib/1.3.1.1`（gzip 压缩矩阵读取，显式 -I/-L/rpath 接入）

## 依赖
- zlib/1.3.1.1（制品仓已发布，上游默认开启 --with-zlib）

## 功能验证
```bash
# 查询版本（安装后）
librsb-config --version
rsbench --version
```

## 参考
- 上游官网：https://librsb.sourceforge.net/
- 上游源码：https://sourceforge.net/projects/librsb/files/
