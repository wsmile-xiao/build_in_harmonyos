# suitesparse 7.8.3 编译笔记（HarmonyOS PC · CMake）

## 定位

SuiteSparse 稀疏矩阵算法套件。本配方**只建 cvxopt 所需的 7 个子库**：
`suitesparse_config` / `amd` / `camd` / `ccolamd` / `colamd` / `cholmod` / `umfpack`。

不建 GraphBLAS、SPQR、KLU、ParU、SPEX 等——它们体量大（GraphBLAS 单独就有数十 MB 源码）、
依赖多，且当前无消费方。需要时通过 `SUITESPARSE_ENABLE_PROJECTS` 加回即可。

**动因**：cvxopt 的 `cholmod` / `umfpack` / `amd` 三个模块依赖它们。

## 关键适配

### ① 只建需要的子集

```
-DSUITESPARSE_ENABLE_PROJECTS="suitesparse_config;amd;camd;ccolamd;colamd;cholmod;umfpack"
```

CMake 会自行处理子库间的依赖序（cholmod 依赖 amd/camd/ccolamd/colamd，umfpack 依赖 cholmod）。

### ② BLAS 接线：环境变量 + 预设缓存变量双保险

`SuiteSparseBLAS.cmake` 默认会**逐个 vendor 试**（Intel MKL 64/32、ARM、OpenBLAS、FLAME…），
每次 `find_package(BLAS)`。但第 21 行有个捷径：

```cmake
if ( DEFINED ENV{BLA_VENDOR} )
    set ( BLA_VENDOR $ENV{BLA_VENDOR} )
```

**设 `ENV{BLA_VENDOR}=OpenBLAS` 即直接采纳，解析确定化**，不再逐个试（也避免误命中某个
vendor 后 `add_compile_definitions(BLAS_<vendor>)` 打上错误的宏）。

同时，交叉 toolchain 在文件里 `set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)` 会覆盖命令行，
`find_package(BLAS)` 搜不到 conan 依赖 → 直接预设结果缓存变量：

```
-DBLAS_LIBRARIES=<openblas>/lib/libopenblas_armv8p-r<ver>.so
-DLAPACK_LIBRARIES=<同上>
```

可行的原理：CMake 的 `FindBLAS`/`FindLAPACK` 每个 vendor 分支都由 `if(NOT xxx_LIBRARIES)`
守着，预设即全部跳过搜索、直接采用。

### ③ 关掉 OpenMP

```
-DSUITESPARSE_USE_OPENMP=OFF
```

设备工具链是 clang，SuiteSparse 找 GNU `libgomp` 会落空。
**PyPI 的 cvxopt wheel 正是因为开着 OpenMP 才 vendored 了 `libgomp`**——从源码编不必背这个包袱。

### ④ `SUITESPARSE_USE_STRICT=ON`

SuiteSparse 默认把各 `*_USE_*` 当**偏好**而非硬约束（`SuiteSparsePolicy.cmake:140` 注释明确
说明）。开 STRICT 让上面那些 OFF 成为硬约束，避免它在找不到时悄悄回退到别的实现。

### ⑤ 其余

- `-DSUITESPARSE_USE_FORTRAN=OFF`：本套 7 个子库无需 Fortran（那是 SPQR/ParU 才用）
- `-DSUITESPARSE_USE_64BIT_BLAS=OFF`：本仓 openblas 是 LP64（`dgemm_` 有、`dgemm_64_` 无）
- `-DCMAKE_INSTALL_LIBDIR=lib`：ohos.toolchain 64 位默认装 `lib64/`
- `-DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib`：SDK 的 `llvm/bin` 只有 `llvm-ar`、
  没有 `llvm-ranlib`，而 ohos.toolchain 却把 `CMAKE_RANLIB` 指过去 → 造静态库时 ENOENT
- `-DSUITESPARSE_DEMOS=OFF`：不建示例程序

## 消费方注意

头装在 `include/suitesparse/`，而消费方按 `#include <cholmod.h>` 写（cvxopt 即如此），
故配方声明了 `includedirs = ["include/suitesparse", "include"]`。

`cpp_info.libs` 按**上层在前**排序（umfpack → cholmod → {camd,ccolamd,colamd,amd} →
suitesparseconfig），静态链接场景下顺序才正确。

## 验证

test_package 直接 `#include` 各子库公共头并链接全部 7 个库，做真实稀疏矩阵计算，5 条断言：

- `SuiteSparse_version` 版本查询
- `amd_order` 对 5×5 三对角阵求填充缩减排序，**校验产出是有效置换**（每个下标恰好出现一次）
- `colamd` 列排序
- `cholmod` 对三对角正定阵做 Cholesky 分解并解方程，用 `cholmod_sdmult` 算残差 `‖Ax-b‖ < 1e-10`
  —— 该路径会真正用到 BLAS
- `umfpack` LU 分解解非对称方程，核对精确解

## 状态

built（真机 `conan create -pr:h ohos-native -pr:b ohos-native` + test_package 全绿）
