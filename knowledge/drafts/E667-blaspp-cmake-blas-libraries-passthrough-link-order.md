# E667 blaspp 族 CMake 后端探测：BLAS_LIBRARIES 直通 + 静态链接拓扑序

> 状态: Draft（待审核 promote）| 日期: 2026-09-22
> 来源: feat/blaspp-2024.10.26（设备原生 conan create 首轮 configure 探测全命中）
> 机器可读层: 同目录 `E667-blaspp-cmake-blas-libraries-passthrough-link-order.kv`

## 现象

BLAS++（icl-utk-edu/blaspp）及其下游 LAPACK++ 不走 conan，自带
`cmake/BLASFinder.cmake` / `LAPACKFinder.cmake`，逐候选 `try_compile/try_run`
探测 BLAS 后端（default / Intel MKL / IBM ESSL / OpenBLAS / Apple Accelerate /
generic `-lblas` / AMD ACML）。在鸿蒙设备 + ohpcd 参考库组合上，generic 候选
`-lblas` 必然失败——ohpcd 的 `libblas.a`（blas/3.12.1、lapack/3.12.1 包）是
flang-ohos 编译的 Fortran 静态库，`xerbla.o` 引用 `_FortranAio*`/
`_FortranAStopStatement`，裸 `-lblas` 链接探针报 undefined reference，finder
最终打出 `BLAS++ requires a BLAS library and none was found.` FATAL_ERROR。

## 根因（两个叠加的坑）

1. **Fortran 运行时不可见**：参考 BLAS/LAPACK 的一切名称型探测
   （`-lblas`/`-llapack`，含 CMake 内置 FindBLAS）都无法感知 flang 的
   `libFortranRuntime.a`/`libFortranDecimal.a` 伴随依赖。
2. **交叉编译语义**：Conan CMakeToolchain 设 `CMAKE_SYSTEM_NAME=HarmonyOS`
   ⇒ `CMAKE_CROSSCOMPILING=1`，finder 的 try_run 跳过运行、按「能链接即
   可用」处理（上游显式支持该分支）。副作用：`blas=auto` 时 ILP64 候选也会
   「链接通过」——好在候选遍历顺序是 mangling 外层（ADD_ 首位）、整型内层
   （LP64 `" "` 在 `-DBLAS_ILP64` 之前），首个成功即 break，直通清单下
   LP64 + ADD_（尾下划线）确定性优先命中。

## 解法（上游机制内，零源码补丁）

走 finder 内置的**第一候选 `BLAS_LIBRARIES`/`LAPACK_LIBRARIES` 直通**（用户
显式给定库全路径清单），清单按静态链接拓扑序排列（GNU 单遍语义下也安全，
**消费者在提供者之前**）：

```cmake
BLAS_LIBRARIES   = liblapack.a;libcblas.a;libblas.a;libFortranRuntime.a;libFortranDecimal.a;m
LAPACK_LIBRARIES = liblapack.a;libFortranRuntime.a;libFortranDecimal.a;m
```

- `lapack.a`/`libcblas.a` 是 BLAS 符号的**消费者**，必须排在 `libblas.a`
  （提供者）**之前**；Fortran 运行时收尾。
- cblas 头与 `-lcblas` 的发现：build() 内设 `CPATH`（头搜索）与
  `LIBRARY_PATH`（`-l` 搜索）指向 cblas 包 include/lib（clang 与 gcc 同语义）。
  CBLASConfig 探针命中第一候选（空库清单，cblas 符号已在 BLAS_LIBRARIES 内），
  tester 链接行不再出现 `-lcblas`，全链路单遍安全。
- conan 消费面：`package_info` 设 `cmake_file_name=blaspp` /
  `cmake_target_name=blaspp::blaspp`（与上游 blasppConfig 命名一致——
  lapackpp 就是 `find_package(blaspp)` 消费），`cpp_info.requires` 传递
  `lapack::lapack`、`cblas::cblas`。

## 实测证据（blaspp/2024.10.26，2026-09-22 设备原生 conan create）

```
-DBLAS_FORTRAN_ADD_    yes
Found BLAS library: <lapack包>/lib/liblapack.a;<cblas包>/lib/libcblas.a;
                    <lapack包>/lib/libblas.a;<lapack包>/lib/libFortranRuntime.a;
                    <lapack包>/lib/libFortranDecimal.a;m
Found CBLAS library
Found LAPACK library: <lapack包>/lib/liblapack.a;...;m
```

## 禁止

- ❌ `use_cmake_find_blas=ON` / `BLA_VENDOR=…`：CMake 内置 FindBLAS 同样
  无法感知 Fortran 运行时，探测必失败或误选。
- ❌ 把 `libblas.a` 排在 `liblapack.a`/`libcblas.a` 之前（提供者先于消费者）：
  单遍链接语义下后拉入成员的 BLAS 符号无处解析 → undefined reference。

## 对下游的直接复用

lapackpp 2024.10.26：`find_package(blaspp)` 找到本包后，其自身的 BLAS 探测
与链接序同构——本条与 E668（FetchContent 离线化）两项即 lapackpp 配方的
主要技术预置。
