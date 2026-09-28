# ptscotch 7.0.12 — OHOS（鸿蒙 PC）适配笔记

## 概述

PT-SCOTCH（`gitlab.inria.fr/scotch/scotch`）是 **SCOTCH 的并行（MPI）版本**：在
分布式内存下完成图/网格划分与稀疏矩阵排序。

它与串行版 SCOTCH 出自**同一上游源码树** —— 同一份 tarball，用
`-DBUILD_PTSCOTCH=ON` 即额外产出 `libptscotch*` 与 `ptscotch.h`。但二者是不同的
conan 包：

| 包 | 产物 | 说明 |
|---|---|---|
| `scotch/7.0.12`（他人归档） | `scotch.h`、`libscotch.a` | 仅串行层；**本 PR 不修改该归档** |
| **`ptscotch/7.0.12`（本包）** | `ptscotch.h`、`libptscotch.a`（+ 串行层） | `BUILD_PTSCOTCH=ON` |

**为何拆成独立包而非给 `scotch` 加选项**：`archives/s/scotch` 属他人归档
（最近提交为 `hicmd`），按 SKILL §0.2 铁律不越权修改。仓内已有
`superlu`（串行）/`superlu-dist`（MPI）这一「同名拆分」先例。

**为何需要这个包**：TriBITS 的 `cmake/tpls/FindTPLScotch.cmake` 在
`TPL_ENABLE_MPI` 时**强制要求** `ptscotch.h` 与
`ptscotch ptscotcherr scotch scotcherr` 四个库：

```cmake
IF (TPL_ENABLE_MPI)
   TRIBITS_TPL_FIND_INCLUDE_DIRS_AND_LIBRARIES( Scotch
    REQUIRED_HEADERS ptscotch.h
    REQUIRED_LIBS_NAMES ptscotch ptscotcherr scotch scotcherr )
ELSE()
   ... REQUIRED_HEADERS scotch.h / REQUIRED_LIBS_NAMES scotch scotcherr
ENDIF()
```

而已发布的 `scotch/7.0.12` 只有串行层（`include/` 下仅 `scotch.h`/`scotchf.h`，
无 `ptscotch.h`），故 Trilinos 侧 `with_mpi=True` 时 Scotch TPL 无法开启。

- **构建系统**: CMake
- **产物**: 静态库 `libptscotch.a` / `libptscotcherr.a` / `libptscotcherrexit.a`
  （+ 串行层 `libscotch.a` 等）
- **许可证**: CeCILL-C
- **补丁**: **0 个**（`patches: {}`，未改动上游任何源码）

## 编译环境

| 项 | 值 |
|---|---|
| 目标平台 | OpenHarmony / HarmonyOS PC（aarch64） |
| 编译器 | `/data/service/hnp/bin/clang`（clang 15，target `aarch64-linux-ohos`） |
| Conan | 2.29.1（OHOS 适配版）、profile `ci/conan/profiles/ohos-aarch64` |

## 依赖

| 依赖 | 版本 | 作用 |
|---|---|---|
| `mpich` | 5.0.1.2 | MPI 运行时（与仓内 `trilinos` 同选） |
| `bzip2` | 1.0.8 | 可选压缩后端（`USE_BZ2`） |
| `xz` | 5.6.2 | 可选压缩后端（`USE_LZMA`） |
| `zlib` | 1.3.1 | 可选压缩后端（`USE_ZLIB`） |

均在 ohpcd 已发布（`conan download` 实测）。

## 编译步骤

```bash
conan create archives/p/ptscotch/7.0.12 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 遇到的问题与解决方案

### 1. CMake 的 FindMPI 在 OHOS 上无法解析 MPI

**现象**：configure 阶段找不到 MPI（`MPI::MPI_C` 目标缺失），而上游
`src/libscotch/CMakeLists.txt` 明确 `target_link_libraries(ptscotch PUBLIC scotch MPI::MPI_C)`。

**根因**：CMake 无 `Platform/HarmonyOS.cmake`，且它不会自动采用 conan 依赖里的
MPI wrapper。

**解法**：在 `generate()` 显式给出
`MPI_C_COMPILER` / `MPIEXEC_EXECUTABLE` 指向 mpich 包的 wrapper
（与仓内 `trilinos` / `superlu-dist` 同款做法）。

### 2. 构建期 `dummysizes` 加载 `libmpi.so` 失败 → `make Error 127`

**现象**（实测，可行性验证阶段真实踩到）：

```
[  3%] Generate scotch.h
Error loading shared library libmpi.so.12: (needed by ./dummysizes)
make[2]: *** [src/libscotch/CMakeFiles/scotch_h.dir/build.make:74: src/include/scotch.h] Error 127
```

**根因**：上游在构建期要**运行**自举工具（`dummysizes` / `ptdummysizes`）来
**生成** `scotch.h`、`ptscotch.h` 等头文件。这些工具动态链接 `libmpi.so`，而
构建期的 loader 搜索路径里没有 mpich 的 `lib/`，于是工具起不来 → 生成规则失败
→ make 报 `Error 127`（命令未找到的经典伪装）。

**解法**：在 `build()` 里把 mpich 的 `lib/` 加入 `LD_LIBRARY_PATH` 后再
configure/build。加进去之后同一条命令即成功，并产出
`libptscotch.a` + 生成的 `ptscotch.h`（实测）。

> 说明：这不是「绕过错误」，而是补齐构建期运行自举工具所需的环境 ——
> 上游 CMake 假定 MPI 已在系统路径上，而 conan 的包布局并非如此。

### 3. Fortran 接口关闭

设备无 gfortran。本包 **C 接口完整**（`SCOTCH_dgraph*`、`SCOTCH_strat*` 等
均为 C 符号），关闭 `BUILD_FORTRAN` 不影响 C/C++ 消费方。

## 验证结果

### 消费者测试（test_package，R34 真实调用）

`test.c` 驱动真实的**并行** API 链路：

1. `SCOTCH_dgraphInit(&graf, MPI_COMM_WORLD)` —— 在 MPI 进程集上建立分布式图
2. `SCOTCH_dgraphBuildGrid3D(&graf, 0, 4, 4, 1, 1, 0)` —— **在内存中生成**
   4×4×1 网格图（无需外部数据文件）
3. `SCOTCH_dgraphCheck(&graf)` —— 校验分布式图结构
4. `SCOTCH_stratDgraphMap(&strat, "b")` + `SCOTCH_dgraphPart(&graf, 4, &strat, parttab)`
   —— 求 4 分区划分

断言：四个调用返回码均为 0 且顶点数 > 0（共 5 项）。

### 上游测试（R51 申报）

上游 `src/check/` 提供 `test_scotch_dgraph_check.c` /
`test_scotch_dgraph_order.c` / `test_scotch_dgraph_band.c` 等驱动，经 ctest 注册。
它们需要外部矩阵数据文件，且多以 `mpiexec` 多进程运行；本环境的 `mpiexec`
被沙箱拦截（`prterun` → `signal 31 (Bad system call)`），故
`ENABLE_TESTS=False` 保持包构建精简，消费者侧验证走 test_package 的真实 API
调用（见 `test_package/MANIFEST.yml` 的完整申报表）。

## 已知限制

- **多进程测试未运行**：本环境 `mpiexec` 被沙箱拦截，故只能单 rank 运行
  （API 是 `MPI_COMM_WORLD` 集合操作，单 rank 是合法的退化进程集，
  仍走完 build/check/partition 全链路）。该限制在环境侧，不在本包。
- **Fortran 接口未启用**：设备无 gfortran；C 接口完整。
- **未启用 `BUILD_LIBSCOTCHMETIS`**：上游默认可选，本包与仓内 `scotch` 保持一致
  不启用（避免与 `metis` 包的同名符号冲突）。

## 交付物

| 文件 | 说明 |
|------|------|
| `include/` | `ptscotch.h`（并行 API）、`scotch.h`、`scotchf.h`、`ptscotchf.h` |
| `lib/libptscotch*.a` | 并行层静态库（含 `libscotch.a` 串行层） |
| `licenses/LICENSE_en.txt` | 上游许可证原文 |

**编译结束**: 2026-09-26
**最终状态**: built
