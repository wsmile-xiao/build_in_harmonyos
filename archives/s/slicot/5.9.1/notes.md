# SLICOT 5.9.1 — OpenHarmony PC 适配笔记

## 概览

| 项 | 值 |
|---|---|
| 包名 | slicot |
| 版本 | 5.9.1 |
| 上游 | SLICOT-Reference（Subroutine Library In COntrol Theory） |
| 源码 | `https://github.com/SLICOT/SLICOT-Reference/archive/refs/tags/v5.9.1.tar.gz` |
| sha256 | `37b0c0fc1800454f8d7553a004a5bb6fac9e042fe2b592ce1eec92045ce9b7a1` |
| 构建系统 | CMake（C + Fortran） |
| 产物 | `lib/libslicot.a`（+ CMake config、头文件） |
| 测试 | 上游 examples 的 242 个 CTest，**242/242 通过** |

## 软件简介

SLICOT 是控制系统理论领域的经典 Fortran 77 数值库（约 1500 个例程）：
状态空间/传递函数运算、Riccati 方程、系统辨识、模型降阶、矩阵方程等。
按族命名（AB/AG/BB/BD/DE/DF/DG/DK/FB/FD/IB/MA/MB/MC/MD/NF/SB/SG/TB/TC/
TF/TG/UD 等）。

## 构建要点

### 1. Fortran 工具链（flang-ohos 先例）

设备无 gfortran，用仓内 `flang-ohos/20.1.0` 作 `tool_requires`
（同 blas / lapack / arpack-ng）。OHOS 下的必要设置：

```
CMAKE_Fortran_COMPILER = <flang-ohos>/bin/flang
CMAKE_SYSTEM_NAME      = Linux            # CMake 无 HarmonyOS 平台模块
CMAKE_TRY_COMPILE_TARGET_TYPE = STATIC_LIBRARY   # 跳过链接探针
CMAKE_C/CXX_COMPILER_FORCED = TRUE
CMAKE_EXE_LINKER_FLAGS / CMAKE_Fortran_LINK_FLAGS
    = --sysroot=... -L<sdk>/aarch64-linux-ohos -L<flang>/lib \
      libFortranRuntime.a libFortranDecimal.a -lm
CMAKE_BUILD_PARALLEL_LEVEL = 1            # OHOS make jobserver FIFO 创建失败
```

### 2. 被移除的 LAPACK 老例程（本适配的关键坑）

上游 `src/CMakeLists.txt` 对 6 个已被 LAPACK 移除的例程做**存在性探测**，
探测不到才编译自带副本：

```cmake
INCLUDE(CheckFortranFunctionExists)
MACRO(ADD_ROUTINE_IF_REQUIRED ROUTINE VAR SOURCE_FILE)
    SET(CMAKE_REQUIRED_LIBRARIES PRIVATE BLAS::BLAS LAPACK::LAPACK)
    Check_Fortran_Function_Exists(${ROUTINE} ${VAR})
    IF (NOT ${VAR})
        SET(SOURCES ${SOURCES} ${SOURCE_FILE})   # 用自带实现
    ENDIF()
ENDMACRO()
ADD_ROUTINE_IF_REQUIRED(dgegs HAVE_DGEGS lapack_aux/dgegs.f)
... (zgegs / dlatzm / zlatzm / dgegv / zgegv 同)
```

**问题**：OHOS 必须设 `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`
（flang 精简运行集无法完成链接探针），于是
`Check_Fortran_Function_Exists` **只编译不链接**，任何符号都被判为"存在"→
6 个副本都不编译 → 最终 examples 链接报：

```
ld.lld: error: undefined symbol: dgegv_
ld.lld: error: undefined symbol: dlatzm_
```

**修复**：LAPACK 3.12 确实已移除它们，故把探测结果直接钉为 FALSE，
强制上游编译自带实现：

```python
for var in ("HAVE_DGEGS", "HAVE_ZGEGS", "HAVE_DLAZTM", "HAVE_ZLAZTM",
            "HAVE_DGEGV", "HAVE_ZGEGV"):
    tc.cache_variables[var] = False
```

### 3. 测试开关只在顶层工程生效

上游 CMake：

```cmake
IF(CMAKE_CURRENT_SOURCE_DIR STREQUAL CMAKE_SOURCE_DIR)
    OPTION(SLICOT_TESTING "Build the SLICOT example programs and tests" ON)
```

即：只有作为**顶层工程**（conan create 正是如此）才会构建 examples 与
CTest；被其它工程 add_subdirectory 引入时自动关闭。配方显式设
`-DSLICOT_TESTING=ON` 并真实运行 `ctest`。

## 上游测试（R51）

`examples/` 下 242 个驱动（TAB/TAG/TB/TC/TF/TG/TI/TK/TM/TS/TT/TU/UD 各族），
每个经 `runtest.cmake` 运行并与其 `examples/results/*.res` 参考结果比对：

```
100% tests passed, 0 tests failed out of 242
```

**真实执行、无跳过、无宽松化。**

## test_package 设计（消费者视角）

`test_slicot.py` 用 flang 把一段真实 Fortran 程序链接到**已打包**的
`libslicot.a`（并带上 BLAS / LAPACK / Fortran 运行时闭包），运行后断言数值：

```fortran
CALL MA02AD( 'A', M, N, A, LDA, B, LDB )   ! B = A^T
! 逐元素校验 B(j,i) == A(i,j)，误差必须为 0
```

输出 `SLICOT CONSUMER OK` → 断言通过。这同时证明：归档可用、符号完整、
依赖闭包（含 Fortran 运行时）齐备。

## 已知平台限制

- Fortran 编译器必须用 flang-ohos（设备无 gfortran）；运行期需 SDK 与
  flang 包的 `lib` 在 `LD_LIBRARY_PATH`。
- `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY` 会使**所有**链接型
  CMake 探测失效——凡上游用 `Check_*_Exists` 之类做能力判断的，都需
  按上例显式钉值。
