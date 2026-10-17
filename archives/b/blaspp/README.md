# blaspp

## 简介

BLAS++ 是美国田纳西大学 ICL 实验室（SLATE 项目族）开发的 BLAS 现代化 C++
封装库：在参考 BLAS/LAPACK（或 MKL/OpenBLAS 等后端）之上提供模板化 C++
API、批量（batch）例程与统一的布局/转置枚举，是 LAPACK++（lapackpp）与
SLATE 的前置依赖库。

## 功能

- BLAS Level 1/2/3 全部例程的 C++ 模板封装（s/d/c/z 四精度）
- batch API（batch-gemm/herk/syrk/trsm 等批量线性代数）
- 设备后端抽象（CUDA/HIP/SYCL，可选；鸿蒙包内禁用）
- 标准 CMake 包配置（`find_package(blaspp)` → `blaspp::blaspp`）

## OHOS 适配

- 设备原生 CMake 构建（C++17）；BLAS/LAPACK 后端来自 ohpcd 已发布的
  `lapack/3.12.1`（参考实现 + flang Fortran 运行时）与 `cblas/3.12.1`。
- GPU 后端（cuda/hip/sycl）以 `gpu_backend=none` 禁用，OpenMP 关闭；
  host API 面完整可用。
- 上游 tester 的 testsweeper 依赖（构建期 FetchContent git clone）以同 tag
  源码随配方离线导出，上游 CMakeLists 零改动。
- 与 Linux 的差异：无 GPU/无 OpenMP 后端；静态链接顺序在配方内显式给定
  （详见版本级 notes.md）。

## 依赖关系

- 编译依赖：`lapack/3.12.1`、`cblas/3.12.1`（均 ohpcd 已发布）
- 运行依赖：无动态库依赖（静态库交付；Fortran 运行时符号由依赖链提供）

## 参考资料

- 上游仓库：https://github.com/icl-utk-edu/blaspp
- 版本：v2024.10.26（tag，peeled commit 8d770a94797e000bea098776e1fce7590e9363b2）
- 相关包：lapack/3.12.1、cblas/3.12.1、blas/3.12.1；下游 lapackpp
