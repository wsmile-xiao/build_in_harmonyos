# qpOASES 3.2.1 — 鸿蒙 PC（OHOS aarch64）适配说明

## 1. 概况

| 项 | 值 |
|---|---|
| 上游 | qpOASES（COIN-OR 在线主动集策略 QP 求解器） |
| 版本 | 3.2.1（release tarball） |
| 源码 | https://github.com/coin-or/qpOASES/archive/releases/3.2.1.tar.gz |
| sha256 | `a7d153b4e23ee66bd50cdb6e84291d0084d9967a9c788a4d873440a6b10ca13b` |
| 构建系统 | CMake |
| 依赖 | **无**（自带 `BLASReplacement.cpp` / `LAPACKReplacement.cpp`） |
| 包类型 | 静态库 `libqpOASES.a` + 公共头文件 |
| 适配路径 | A（基础适配） |

## 2. 上游工程结构

```
CMakeLists.txt          # 构建 qpOASES 静态库 + 11 个 example/qrecipe 可执行文件
make.mk                 # 传统 Makefile 入口（硬编码本机 g++，仅适用于本机编译）
src/*.cpp               # 库源码（含自带 BLAS/LAPACK 替代实现）
include/qpOASES.hpp     # 公共头文件入口
include/qpOASES/*.hpp   # 22 个头文件 + 11 个 .ipp 实现文件
testing/runUnitTests    # 上游测试驱动脚本
testing/cpp/*.cpp       # 30 个上游单元测试源文件
testing/cpp/data/fetch_cpp_data  # 外部 problem data 拉取脚本（SVN）
```

## 3. 适配要点

### 3.1 零外部依赖

qpOASES 自带 BLAS 与 LAPACK 的替代实现（`src/BLASReplacement.cpp`、
`src/LAPACKReplacement.cpp`），不链接任何外部数值库，因此交叉编译不存在
依赖链问题。CI 的 L0i 依赖闸自然通过。

### 3.2 CMake 平台模块（E092）

CMake 不提供 `Platform/HarmonyOS.cmake`。OHOS 工具链已把 target 定为
`aarch64-linux-ohos`，因此配方在 `generate()` 中显式 pin：

```python
tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
```

不 pin 会命中 `System is unknown to cmake`（知识库 E092）。

### 3.3 静态库为唯一形态

上游 `CMakeLists.txt` 第 105 行硬编码：

```cmake
ADD_LIBRARY(qpOASES STATIC ${SRC})
```

`shared` 选项在该上游版本无法生效，因此 `manifest.yaml` 中明确记录
产物恒为静态库，`test_package` 也按静态库链接。

### 3.4 上游测试的复用方式（关键）

上游的测试构建入口是 `testing/cpp/Makefile`，它 `include ../../make.mk`，
而 `make.mk` 把 `CPP` 硬编码为本机 `g++` 并用本机 flags，**无法复用于交叉
编译**。但 `testing/cpp/test_*.cpp` 这 30 个源文件是彼此独立的翻译单元，
只依赖：

* `testing/cpp/` 下的本地头（`test_qrecipe_data.hpp` 等）
* 公共头文件目录 `include/`
* 库本体 `libqpOASES.a`

因此配方在 `build()` 中用显式交叉编译器逐文件编译（编译器路径与 sysroot
来自 conan profile 的 `tools.build:compiler_executables` 与
`tools.build:sysroot`，不硬编码本机环境），再用 `run-ohos-tests.py` 按
`testing/runUnitTests` 的顺序与退出码语义执行。

**未修改任何上游测试源文件。**

## 4. 上游测试的退出码语义与数据缺失

`testing/runUnitTests` 的判定逻辑：

| 退出码 | 上游含义 | 本配方归类 |
|---|---|---|
| `0` | 通过 | PASS |
| `99` | `problem data missing!` | 数据缺失（非失败） |
| 其他 | `failed!` | FAIL |

外部数据集由 `testing/cpp/data/fetch_cpp_data` 从
`https://projects.coin-or.org/svn/qpOASES/misc/testingdata/cpp` 拉取，
**该 COIN-OR SVN 服务已下线**，任何用户（包括上游自身）现在都无法取得这批
数据。因此依赖该数据集的 `test_hs268`、`test_constraintProduct1/2`、
`test_runAllOqpExamples` 与 `test_bench`（`Odd`/`Ods`/`Omd` 三个参数）
共 7 次执行返回 99。

其余 24 次执行（覆盖矩阵运算、工作集索引、QP/LP/稀疏/热启动/不可行/
无界/自定义回调等全部主要求解路径）均真实执行并返回 0。

### 4.1 补丁：test_example2 的堆释放后使用（UB）

`testing/cpp/test_example2.cpp` 在最后一项断言中先释放再读取：

```cpp
delete[] Primal_Dual_Var;
delete[] Var;

QPOASES_TEST_FOR_NEAR( Primal_Dual_Var[3*5+3], 26.0 );   /* 释放后使用 */
```

这是堆释放后使用（undefined behaviour），在本机 x86_64 上用 ASan 可直接复现：

```
==288143==ERROR: AddressSanitizer: heap-use-after-free
SUMMARY: AddressSanitizer: heap-use-after-free
         testing/cpp/test_example2.cpp:123:3 in main
```

该 UB 在 aarch64/OHOS 上表现为 `test_example2` 退出码 1，即上游套件会报出一个
**由测试自身缺陷（而非求解器）导致的失败**。补丁把这次读取上移到释放之前，
保留原有断言语义，不触碰任何求解逻辑。

仅修正该读取后，`test_example2` 在 OHOS aarch64 上两项 KKT 断言均通过
（`maxKktViolation` = 2.78e-17 与 5.55e-16，容限 1e-15 / 2e-15），
方差协方差项等于期望值 26.0。

## 5. 验证口径

* 上游用例：`testing/cpp` 下 **30** 个测试源文件，`runUnitTests` 共发起
  **31** 次执行（`test_bench` 以 3 个参数各跑一次）。
* 实测（`conan create -pr:h=ohos-aarch64-run`，测试经 qemu 执行）：
  31 次执行中 **24 次给出判定且全部通过**；7 次因外部数据集缺失返回 99
  （上游约定）。**失败 0**。
* 可测部分通过率 **24/24 = 100%**。
* 消费者用例：`test_package/test_qpoases.cpp`，**14 项断言全过**，在 OHOS
  aarch64 上经 qemu 真实执行。用例求解上游 `example1` 的经典 QP 并逐项校验
  解析最优解 `x*=(0.5,-1.5)`、起作用约束、界约束、对偶解 `(1.75,0,0.25)`、
  目标值 `-0.0625`，再经 `SQProblem::hotstart` 热启动换目标/界/约束，校验
  `x*=(0,-1)`、目标值 `-1.25` 与工作集接口，另校验 `getNorm`。
* 交叉验证：同一消费者用例在本机 x86_64 原生编译执行，输出与 OHOS aarch64
  结果**逐位一致**（`x=[0.500000000000 -1.500000000000]`，
  `obj=-0.062500000000`；热启动后 `x=[0.000000000000 -1.000000000000]`，
  `obj=-1.250000000000`）。

## 6. 已知限制

1. 上游 `test_hs268` / `test_constraintProduct1/2` / `test_runAllOqpExamples`
   / `test_bench` 因外部数据集源（COIN-OR SVN）已停服而无法执行判定；这是
   上游自身的数据获取渠道失效，非适配缺陷。若后续需要覆盖该路径，需另行
   托管数据集，本次不做。
2. 上游 `CMakeLists.txt` 的 `PROJECT(... CXX)` 未声明 C 语言，CMake 会忽略
   `CMAKE_C_COMPILER`（配置日志中的 `Manually-specified variables were not
   used` 提示）。本项目为纯 C++，无影响。
