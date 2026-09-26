# superlu-dist 9.0.0 — OHOS（鸿蒙 PC）适配笔记

## 概述

SuperLU_DIST（`github.com/xiaoyeli/superlu_dist`）是 **SuperLU 的分布式内存版本**：
按 MPI 进程网格划分矩阵，用 ParMETIS 做填充约减排序，求解大型稀疏非对称线性方程组。
它是 Trilinos / Amesos2 的 `SuperLUDist` TPL 的上游。

> ⚠️ 与仓内 `superlu/7.0.1` 是**两个不同的包**：`superlu` 是串行版（单进程直接
> 分解），`superlu-dist` 是 MPI 分布式版，二者不可互相替代（Trilinos 的
> `FindTPLSuperLUDist.cmake` 与 `FindTPLSuperLU.cmake` 分别对应）。

- **构建系统**: CMake（上游 `cmake_minimum_required(VERSION 3.18.1)`）
- **产物**: 静态库 `libsuperlu_dist.a`（`package_type=library`）
- **许可证**: BSD-3-Clause（上游 `License.txt` 含第 3 条「Neither the name of …」）
- **补丁**: **0 个**（`patches: {}`，未改动上游任何源码）

## 编译环境

| 项 | 值 |
|---|---|
| 目标平台 | OpenHarmony / HarmonyOS PC（aarch64） |
| 编译器 | `/data/service/hnp/bin/clang{,++}`（clang 15，target `aarch64-linux-ohos`） |
| CMake | 4.1.2（`/data/service/hnp/cmake.org/cmake_4.1.2`） |
| Conan | 2.29.1（OHOS 适配版）、profile `ci/conan/profiles/ohos-aarch64` |

## 依赖

| 依赖 | 版本 | 作用 | 来源 |
|---|---|---|---|
| `open-mpi` | 5.0.10 | MPI 运行时（进程网格与通信） | ohpcd 已发布 |
| `parmetis` | 4.0.3 | 并行填充约减排序（自带 METIS） | ohpcd 已发布 |
| `openblas` | 0.3.33 | BLAS/LAPACK | ohpcd 已发布 |

**MPI 实现必须与 parmetis 一致**：`parmetis/4.0.3` 的配方硬绑
`open-mpi/5.0.10`（`conaninfo.txt` 的 `[requires]` 为 `open-mpi/5.0.Z`）。
若本包改用 `mpich`，会在依赖图上要求同一进程存在两份 MPI 运行时而冲突，
故三者统一用 open-mpi。

## 编译步骤

```bash
conan create archives/s/superlu-dist/9.0.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -c tools.build:jobs=2 --build=missing
```

## 遇到的问题与解决方案

### 1. `find_package(MPI)` 失败（`Could NOT find MPI_C (missing: MPI_C_LIB_NAMES MPI_C_WORKS)`）

**现象**：上游 `CMakeLists.txt:173` 的 `find_package(MPI REQUIRED)` 直接失败，
CMake 报 `Could NOT find MPI (missing: MPI_C_FOUND MPI_CXX_FOUND)`。

**根因（两层）**：

1. **CMake 不识别 OHOS 平台**。OHOS 的 conan profile 会让 CMakeToolchain 设
   `CMAKE_SYSTEM_NAME=HarmonyOS`，而 CMake 没有 `Platform/HarmonyOS.cmake`，
   于是打印「System is unknown to cmake」并被判为**交叉编译** ——
   FindMPI 的探测需要「编译 + 链接 + 运行」，交叉编译下 `try_run` 全部失败。
2. **open-mpi 的 wrapper 无法独立运行**。FindMPI 会执行 `mpicc` 来反解编译/链接
   参数，而 `mpicc` 是 `opal_wrapper` 的软链，运行期需要两样环境：
   - `OPAL_PREFIX` —— 否则去 `//share/openmpi/` 找数据文件，报
     `Cannot open configuration file //share/openmpi/mpicc-wrapper-data.txt`；
   - `LD_LIBRARY_PATH` 指向本包 `lib/` —— 否则报
     `Error loading shared library libpmix.so.2 / libevent_core-2.1.so.7 / libhwloc.so.15`
     （这些 .so 都在包内，但不在 loader 搜索路径上）。

**解法**（均在 `conanfile.py` 内，未改上游源码）：

- 用 `user_toolchain` block 把 OHOS 呈现为 Linux 且 `CMAKE_CROSSCOMPILING FALSE`
  （与仓内 `trilinos` / `bliss` / `neovim-qt` 同款做法）；
- 生成一层 shell wrapper，设好 `OPAL_PREFIX` + `LD_LIBRARY_PATH` 再 `exec`
  依赖包的 `mpicc`/`mpicxx`/`mpiexec`，并把该 wrapper 交给
  `MPI_C_COMPILER`/`MPI_CXX_COMPILER`/`MPIEXEC_EXECUTABLE`。

修复后：`-- Found MPI_C: …/libmpi.so (found version "3.1")`、
`-- Found MPI: TRUE (found version "3.1")`。

### 2. 消费者编译报 `fatal error: 'mpi.h' file not found`

**现象**：`test_package` 编译 `test.c` 时找不到 `mpi.h`。

**根因**：本包的**公开头**直接包含 `<mpi.h>`
（`SRC/include/superlu_defs.h:56`），因此消费者的编译行必须有 MPI 头文件目录。
但制品仓 `open-mpi/5.0.10` 经 CMakeDeps 生成的配置中
`open-mpi_INCLUDE_DIRS_RELEASE` 为**空**（实测），导致 `MPI::MPI_C`
目标不带 include 目录。

该缺陷位于他人归档（`archives/o/open-mpi`），按 SKILL §0.2 铁律不越权修改，
故在**本包侧**把 MPI 头目录转发给下游
（`package_info()` 里 `cpp_info.includedirs.append(<open-mpi>/include)`）。

### 3. 消费者链接报 `undefined symbol: __kmpc_*`（195 个）

**现象**：链接 `test_superlu_dist` 时报大量 OpenMP 符号未定义。

**根因**：上游 `CMakeLists.txt` 默认 `enable_openmp=TRUE`，会
`find_package(OpenMP)` 并把 `-fopenmp` 加进 `CMAKE_C_FLAGS`。设备 clang 支持
OpenMP（实测 `-fopenmp` 可用，SDK 内 `libomp.a`/`libomp.so` 齐全），于是静态库内
保留了 `__kmpc_*` / `omp_*` 符号。静态库不做未定义符号检查，但消费者链接时
必须能解析它们。

**解法**：在 `package_info()` 用**链接标志**而非 `system_libs` 传递：

```python
self.cpp_info.exelinkflags = ["-fopenmp"]
self.cpp_info.sharedlinkflags = ["-fopenmp"]
```

**为什么不能用 `system_libs=["omp"]`（= 裸 `-lomp`）**：实测那样二进制的
`DT_NEEDED` 里会有 `libomp.so`，却**不带 RUNPATH**，运行期报
`Error loading shared library libomp.so: (needed by ./test_superlu_dist)`。
而 `-fopenmp` 由 clang 驱动链接时会同时加上
`RUNPATH=/data/service/hnp/…/llvm/lib`（`llvm-readelf -d` 实测可见），二进制可直接运行。
仓内先例：`archives/p/perceptualdiff/2.1` 用 `exelinkflags=-fopenmp=libomp`。

> 这里刻意**没有**用 `enable_openmp=FALSE` 关掉 OpenMP —— 那会为了好构建而阉割
> 上游真实的并行分解能力（R40 关注点）。

### 4. `test()` 阶段 `Signal 11 (core dumped)`

**现象**：首次跑通链接后，`test()` 运行时段错误。

**根因**：这是**测试代码自身的缺陷**，不是库的问题 —— 我最初把矩阵数组建在
**栈上**，而 `Destroy_CompCol_Matrix_dist()` 会对它们调用 `SUPERLU_FREE`，
于是释放了非法内存。

**解法**：改用库自带分配器 `intMalloc_dist` / `doubleMalloc_dist` 分配，
并由 `Destroy_CompCol_Matrix_dist` 释放（与上游
`EXAMPLE/pddrive_ABglobal.c` 的 `dallocateA_dist` 用法一致）。

## 验证结果

### 消费者测试（test_package，R34 真实调用）

`test.c` 通过真实分布式 API `pdgssvx_ABglobal` 求解 5×5 三对角稀疏方程组，
断言解向量与精确解误差 < 1e-8，并独立重算残差 `||Ax-b||inf` < 1e-8。
矩阵按全局 CSC（`SLU_NC`）在内存组装，**不需要外部数据文件**。

实测输出：

```
SuperLU_DIST version:	9.0.0
Process grid:		1 X 1
solution max error = 0.000e+00
residual ||Ax-b||inf = 0.000e+00
PASSED: SuperLU_DIST solved the system to 1e-8
```

`conan create` 端到端结果：**`[exit] 0`**（主包构建 + test_package 全通过）。

### 上游测试（R51 申报）

上游 `TEST/` 目录提供 `pdtest.c` / `pztest.c` 等驱动，通过 ctest 注册。
这些驱动**需要外部矩阵数据文件**（Harwell-Boeing `.rua` / `.cua`），
故本配方设 `enable_tests=OFF` 保持包构建精简，消费者侧验证走 test_package
的真实 API 求解（见 `test_package/MANIFEST.yml` 的完整申报表）。

## 已知限制

- **ParMETIS 的许可证**：`parmetis/4.0.3` 为 University of Minnesota 的
  「research/education 免费」条款（非标准 OSI 许可证）。本包通过 conan
  依赖引用它，未再分发其源码。
- **未启用 Fortran 接口**：`XSDK_ENABLE_Fortran=OFF`。设备无 gfortran；
  本包的 **C 接口**已完整（所有求解入口均为 C 符号）。若下游需要 Fortran
  接口，需先补齐 Fortran 工具链。
- **未启用 CUDA/HIP/CombBLAS**：上游默认关闭，OHOS 无 GPU 驱动栈 / 未适配。
- **测试未跑多进程**：test_package 以单 rank 运行（OpenMPI 的 singleton init），
  验证的是求解正确性而非进程网格扩展性；多进程需 `mpiexec`，在 conan
  test() 内不便保证 launcher 可用。

## 交付物

| 文件 | 说明 |
|------|------|
| `include/` | 公开头（`superlu_defs.h`、`superlu_ddefs.h`、`supermatrix.h`、`superlu_enum_consts.h` 等） |
| `lib/libsuperlu_dist.a` | 静态库（`BUILD_SHARED_LIBS=OFF`） |
| `licenses/License.txt` | 上游许可证原文 |

**编译结束**: 2026-09-25
**最终状态**: built
