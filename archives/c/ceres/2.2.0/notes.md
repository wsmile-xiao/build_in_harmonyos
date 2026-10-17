# ceres 2.2.0 — HarmonyOS PC 适配说明

## 一、范围

- 上游：Ceres Solver（`https://github.com/ceres-solver/ceres-solver`），版本 **2.2.0**
- 交付：`archives/c/ceres/2.2.0/`（配方 + 消费者测试 + 文档）
- 产物：**静态库 `lib/libceres.a`**（`shared=False` 默认；顺带剔除未请求的 `.so` 变体）
- 目标：OHOS PC（aarch64，OHOS SDK v7.0 / clang 15.0.4 / libc++15 / cppstd=17）

## 二、上游事实（一手核对）

| 项 | 值 |
|---|---|
| 构建系统 | CMake，`cmake_minimum_required(VERSION 3.16...3.27)` |
| C++ 标准 | 上游要求 C++17（与 profile `compiler.cppstd=17` 匹配） |
| 必需依赖 | `find_package(Eigen3 3.3 REQUIRED)`（CMakeLists.txt:185） |
| 可选依赖 | Glog（`MINIGLOG` 可替代）、gflags、SuiteSparse、LAPACK、CUDA、Python、benchmark |
| 默认开关 | `BUILD_SHARED_LIBS=OFF`、`BUILD_TESTING=ON`、`BUILD_EXAMPLES=ON`、`BUILD_BENCHMARKS=ON`、`SCHUR_SPECIALIZATIONS=ON` |
| 上游测试 | gtest 用例 **909 项**（`grep -rhoE '^TEST(_F)?\(' . --include=*.cc \| wc -l`，分布于 175 个 `internal/ceres/*_test.cc`） |

## 三、依赖与构建口径

**依赖链只剩 Eigen**：

```
requires("eigen/3.4.1")         # header-library；上游 find_package(Eigen3 3.3) 由 CMakeDeps 直接满足
```

上游开关设置（`generate()`）：

| 变量 | 值 | 理由 |
|---|---|---|
| `BUILD_SHARED_LIBS` | OFF | 只交付静态库（与仓库既有归档口径一致） |
| `MINIGLOG` | ON | 用上游自带的极简 glog 替身，**不需要 glog 包** |
| `GFLAGS` | OFF | 示例/工具才需要 |
| `SUITESPARSE` / `LAPACK` / `USE_CUDA` | OFF | 稀疏求解走 Eigen（`EIGENSPARSE=ON`） |
| `BUILD_TESTING` / `BUILD_EXAMPLES` / `BUILD_BENCHMARKS` / `BUILD_DOCUMENTATION` | OFF | 单包预算；上游测试口径另在 MANIFEST 如实申报 |
| `CMAKE_INSTALL_RPATH` | `$ORIGIN` | 共享变体下的运行库定位（静态交付时无影响） |

`package_info()` 里声明 `cpp_info.requires = ["eigen::eigen"]`，并把 MINIGLOG 的 include 目录
一并导出（见第四节第 2 条）。

## 四、OHOS 适配要点（三处值得记录的坑）

### 1. Eigen 是传递依赖，消费者侧必须显式声明

test_package 只 `requires(ceres)` 时，Conan **不会**为传递依赖生成 CMakeDeps 配置，
且 `cpp_info.includedirs` 可能取到相对路径 → 消费者编译报
`fatal error: 'Eigen/Core' file not found`。
本包两处都做了：配方 `cpp_info.requires` 声明 + test_package 显式 `requires("eigen/3.4.1")`，
并在回退路径里把 include 目录统一转成**绝对路径**。

### 2. MINIGLOG 的 include 面必须镜像上游 INSTALL_INTERFACE（本包唯一“额外”配置）

Ceres 的**公共头文件**会无条件 `#include "glog/logging.h"`。MINIGLOG 模式下该 include 由
上游自带的 miniglog 头满足，而上游是这样导出的（`internal/ceres/CMakeLists.txt`）：

```cmake
target_include_directories(ceres BEFORE PUBLIC
  $<BUILD_INTERFACE:${Ceres_SOURCE_DIR}/internal/ceres/miniglog>
  $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}/ceres/internal/miniglog>)
```

Conan 的 `cpp_info.includedirs` 默认只有 `include` → 消费者报
`fatal error: 'glog/logging.h' file not found`。**修法：在 `package_info()` 里镜像该目录**：

```python
if not self.options.with_glog:
    self.cpp_info.includedirs = ["include", "include/ceres/internal/miniglog"]
```

### 3. 上游 `FindGlog.cmake` 识别不了 Conan 生成的 glog 配置

实测：即使 CMakeDeps 已声明 `glog::glog`（configure 日志出现
`Conan: Target declared 'glog::glog'`），上游仍以 `GLOG_FOUND` 为空走到
`FATAL_ERROR: Can't find Google Log (glog)`。因此默认不启用真实 glog（`with_glog=False`）；
若确需真实 glog，需要额外处理上游 FindGlog 的识别逻辑（本包提供 `with_glog` 开关，但默认关闭）。

> 这也是选择 MINIGLOG 的直接原因：**依赖更少、且上诉识别问题不存在**。

## 五、测试

### 上游测试：N=909，本轮执行 0（如实申报）

未执行原因：运行上游测试需引入 googletest 并额外编译约 175 个测试翻译单元，构建成本远超单包预算。
**未修改、未删除、未伪造任何上游测试源码**；分母 909 为上游实测真值，未缩小。
（判定口径见 `test_package/MANIFEST.yml`。）

### 消费者测试：15 项断言，全部真实执行

`test_package/test_ceres.cpp`（由 `add_test` 注册进 ctest）：

| # | 断言 | 类型 |
|---|---|---|
| 1 | `CERES_VERSION_STRING` 以 `2.` 开头 | 头文件/版本 |
| 2–3 | `ceres::Jet` 标量运算（3×3+2=11）与导数传播（d/dx=6） | 自动微分基础设施 |
| 4–7 | `Problem.NumResidualBlocks==5`、`NumParameterBlocks==2`、`HasParameterBlock(&m/&c)` | 记账 API |
| 8–13 | `IsSolutionUsable()`、`termination_type==CONVERGENCE`、拟合斜率 m≈2、截距 c≈1（1e-8 内）、`final_cost≈0`、`num_residual_blocks==5` | **真实数值求解**（`AutoDiffCostFunction` 拟合 y=2x+1） |
| 14 | `AngleAxisRotatePoint`：(1,0,0) 绕 z 轴 90° → (0,1,0) | `rotation.h` 实函数 |
| 15 | `EuclideanManifold<2>` 的 AmbientSize/TangentSize == 2 | Manifold 接口 |

## 六、本机验证（★ 真实执行到哪一步就说到哪一步）

```
1) conan create（x86-64 → OHOS aarch64 交叉）
   → exit=0；ceres/2.2.0 打包成功
   → test_package：find_package(Ceres) 找到 Conan 生成的配置，链接 Ceres::ceres 成功（交叉环境不执行）

2) 全静态链接 + QEMU 真跑（scripts/ohos/verify-ceres-runtime.sh）
   → 链接 rc=0；ELF 64-bit LSB executable, ARM aarch64, statically linked
   → INTERP 段数量 0
   → qemu-aarch64-static 执行：
        checks: 15  failures: 0
        ALL PASS
   → consumer exit=0
```

**为什么本机能真跑**：交付物是静态归档，消费者再与 SDK 的静态
`libc++.a/libc++abi.a/libunwind.a` 全静态链接 → 产物 `INTERP` 段为 0，
不需要 OHOS 的动态加载器（本机没有可用形态的 `ld-musl-aarch64.so.1`）。
设备端原生构建（官方 CI aarch64 worker）下 test_package 走原生分支，直接以 ctest 执行。

## 七、局限（如实说明）

1. 上游 909 个 gtest 用例本轮未执行（原因见第五节），本地层给出的证据是
   「真实编译 + 真实链接 + **真实执行**的 15 项消费者断言」，不是“跑过全部单测”。
2. 本机是交叉编译，与官方 CI 的设备端原生编译不等价；本地层不替代 CI。
3. 构建内存：Ceres 的 `schur_eliminator_*` / `partitioned_matrix_view_*` 模板 TU
   单文件编译峰值内存 1–2 GB；在 7 GB 的默认 WSL2 上按 `nproc` 并行会被 OOM killer 杀掉
   （Error 137）甚至拖挂整个 WSL VM。本机固定用 `-c tools.build:jobs=N`（CI 侧本身是 `make -j1`）。

## 八、复用知识

1. **上游 INSTALL_INTERFACE 必须镜像进 cpp_info**（本例：MINIGLOG 的 `include/ceres/internal/miniglog`），
   否则「上游自测能过、消费者编译不过」。
2. **上游 FindGlog 之类自研 Find 模块常常认不出 Conan 生成的 config**：先看 configure 日志里
   是否出现 `Conan: Target declared '<dep>::<dep>'`，再决定是走 MINIGLOG/关闭该依赖，
   还是去适配上游的查找逻辑。
3. **传递依赖要在消费者侧显式声明**（头文件型依赖尤其），并把 include 目录转成绝对路径。
4. **模板密集库要限制并行度**（`-c tools.build:jobs=N`），不要用默认 `nproc`。
5. Eigen 制品仓包是 header-library，`cmake_file_name=Eigen3`/target `Eigen3::Eigen`，
   凡是上游 `find_package(Eigen3 3.3 REQUIRED)` 的库都能零补丁满足。
