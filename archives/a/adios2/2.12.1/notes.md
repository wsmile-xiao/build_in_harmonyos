# ADIOS2 2.12.1 适配笔记

## 编译环境

- 构建系统：CMake
- 编译日期：2026-07-18
- 目标平台：OHOS armv8
- 编译器：Clang / Clang++
- 状态：built

## 版本来源

- 版本依据：Homebrew 官方 adios2 Formula 当前稳定版本
- 上游版本：2.12.1
- 源码 SHA256：71edd8f721448311852122fca8d83ae497b43846e5bfcdfd275dc06bb7f3d0c5

## 首轮适配范围

- 启用串行 C/C++ 核心 API
- 启用 BP 文件读写能力
- 构建静态库
- 使用上游内置 pugixml、nlohmann_json 和 yaml-cpp
- 禁用 MPI、Fortran、Python、SST、HDF5、ZeroMQ 和可选压缩后端

## 测试策略

- 上游完整测试依赖 GTest、Python 和多种可选后端，首轮核心适配不构建（`BUILD_TESTING=OFF`）
- test_package 使用公开 C++ API 写入并读取 BP 数据
- 真机验证静态库链接、BP5 文件创建和数据往返一致性

### 上游测试用例数统计（2026-07-20 补充）

对上游 `testing/` 目录的 CMakeLists.txt 进行静态解析，统计 CMake 注册的测试入口数：

| 项 | 数量 | 说明 |
|---|---|---|
| `gtest_add_tests_helper` 调用 | 201 | 分布在 28 个 CMakeLists.txt，每次调用通过 `gtest_add_tests` 自动扫描源文件中的 `TEST/TEST_F/TEST_P` 宏注册用例 |
| `add_test` 调用 | 127 | 分布在 17 个 CMakeLists.txt，含 `SetupTestPipeline` 注册的 Setup/Cleanup fixture |
| `.cpp` 中 GTest 宏 (`TEST/TEST_F/TEST_P`) | 267 | 分布在 100 个测试源文件 |
| `.F90` 中 GTest 宏 | 0 | Fortran 测试通过 `gtest_add_tests_helper_Fortran` + `add_test` 显式注册 |
| **CMake 注册入口合计** | **328** | `gtest_add_tests_helper` 201 + `add_test` 127 |

`gtest_add_tests_helper` 函数定义位于 `testing/CMakeLists.txt`，其语义为：
- `MPI_NONE`：仅注册 Serial 版本，每个 `TEST/TEST_F/TEST_P` 生成 1 个 ctest 用例
- `MPI_ALLOW`：Serial + MPI 各注册一份，每个宏生成 2 个 ctest 用例
- `MPI_ONLY`：仅注册 MPI 版本，每个宏生成 1 个 ctest 用例

部分测试通过宏进一步展开，例如 `testing/adios2/engine/bp/CMakeLists.txt` 中的：
- `bp_gtest_add_tests_helper`：同一源文件针对 BP3/BP4/BP5 各注册一次（×3）
- `bp3_bp4_gtest_add_tests_helper`：针对 BP3/BP4 各注册一次（×2）
- `async_gtest_add_tests_helper`：针对 6 种异步聚合策略各注册一次（×6）

因此**实际 `ctest -N` 列出的用例数**会因配置（BP3/BP4/BP5、Serial/MPI、SST/DataMan 等后端启用情况）动态变化，完整配置下估计在 500-800 个用例之间。

### 上游测试通过率

- **通过率：0/328（未执行）**
- 原因：首轮核心适配禁用 `BUILD_TESTING`，上游 `testing/` 目录不参与构建
- 替代验证：使用公开 C++ API 完成 BP5 写入→随机访问读取→数据一致性断言，并使用上游 `bpls` 复核文件元数据（详见"验证结果"小节）
- 后续扩展：启用 `BUILD_TESTING=ON` 需要先解决 GTest 依赖（上游 `ADIOS2_USE_EXTERNAL_DEPENDENCIES=OFF` 时会从 source 拉取），并按需启用 MPI/SST/HDF5 等后端以覆盖对应测试子集

### 上游 testing/ 目录结构概览

| 子目录 | 主要内容 | 首轮是否适用 |
|---|---|---|
| `testing/adios2/engine/bp/` | BP3/BP4/BP5 引擎读写测试（核心） | 适用，但需 GTest |
| `testing/adios2/engine/bp/operations/` | BP 引擎压缩算子测试 | 不适用（Blosc2/SZ/ZFP 等后端未启用） |
| `testing/adios2/engine/inline/` | Inline 引擎测试 | 适用 |
| `testing/adios2/engine/null/` | Null 引擎测试 | 适用 |
| `testing/adios2/engine/hdf5/` | HDF5 引擎测试 | 不适用（HDF5 未启用） |
| `testing/adios2/engine/dataman/` | DataMan 引擎测试 | 不适用（DataMan 未启用） |
| `testing/adios2/engine/sst/` | SST 引擎测试 | 不适用（SST 未启用） |
| `testing/adios2/engine/ssc/` | SSC 引擎测试 | 不适用（需 MPI） |
| `testing/adios2/engine/mhs/` | MHS 引擎测试 | 不适用（MHS 未启用） |
| `testing/adios2/engine/staging-common/` | Staging 通用测试 | 不适用（需 SST/EVPath） |
| `testing/adios2/engine/time-series/` | Time-Series 引擎测试 | 适用 |
| `testing/adios2/helper/` | 辅助功能测试（Strings/DivideBlock/MinMaxs 等） | 适用 |
| `testing/adios2/interface/` | ADIOS 公共 C++ 接口测试 | 适用 |
| `testing/adios2/yaml/` | YAML 配置测试 | 适用 |
| `testing/adios2/xml/` | XML 配置测试 | 适用 |
| `testing/adios2/hierarchy/` | BP 层级读取测试 | 适用 |
| `testing/adios2/derived/` | 派生变量测试 | 适用（部分需 MPI） |
| `testing/adios2/unit/` | 单元测试（PosixTransport/FilePool 等） | 适用 |
| `testing/adios2/bindings/C/` | C 绑定测试 | 适用 |
| `testing/adios2/bindings/fortran/` | Fortran 绑定测试 | 不适用（Fortran 未启用） |
| `testing/adios2/bindings/python/` | Python 绑定测试 | 不适用（Python 未启用） |
| `testing/adios2/gpu-backend/` | GPU 后端测试（Kokkos） | 不适用（CUDA/Kokkos 未启用） |
| `testing/adios2/backward_compatibility/` | 向后兼容性测试 | 适用 |
| `testing/adios2/output_archive/` | 输出归档测试 | 适用 |
| `testing/adios2/performance/` | 性能测试 | 适用（部分需 MPI） |
| `testing/utils/iotest/` | IOTest 工具测试集 | 不适用（需 MPI） |
| `testing/utils/cwriter/` | CWriter 测试 | 适用 |
| `testing/utils/bpcmp/` | BP 文件比较工具测试 | 适用 |
| `testing/utils/changingshape/` | 变化形状测试 | 不适用（需 MPI） |
| `testing/install/` | 安装测试 | 适用 |
| `testing/h5vol/` | HDF5 VOL 测试 | 不适用（HDF5 未启用） |
| `testing/examples/` | 示例测试 | 适用 |

## 验证结果

- 真机环境：HarmonyOS PC aarch64，Clang 15.0.4，Conan 2.29.1，CMake 4.1.2
- 构建配置：OHOS armv8、C++17、libc++、Release、静态库
- `conan create`：通过，退出码 0
- CI 定向门禁：L0、L1、L2、L4、L5 全部通过，总计 1 个包、成功 1、失败 0
- 破坏性负向测试：临时移除包内 `bin/`、`lib/` 和 `include/` 后测试按预期失败，确认 test_package 真实依赖 ADIOS2 制品
- Conan 包：包含 8 个静态库、43 个头文件、66 个 CMake 配置文件和 `adios2-config`
- test_package：通过，输出 `ADIOS2 BP round-trip passed`
- `adios2-config`：`--prefix`、`--version`、`--cflags`、`--cxxflags`、`--libs` 均通过，并使用其输出直接编译、静态链接和运行 BP5 回环程序
- 上游 `bpls`：成功读取测试生成的 BP5 文件，识别 `int32_t values {4} = 3 / 13`
- 上游完整 CTest：未执行；首轮适配关闭 `BUILD_TESTING`，完整测试还需要 GTest、Python 和可选后端
- 替代验证：使用公开 C++ API 完成 BP5 写入、随机访问读取及数据一致性断言，并使用上游 `bpls` 复核文件元数据
- 风险：MPI、Fortran、Python、SST、DataMan、HDF5 和压缩后端未覆盖
- 非阻塞警告：HMDFS 不支持 GNU Make jobserver FIFO，Make 回退后构建仍成功

## 已知限制

- 不提供 MPI 并行 I/O
- 不提供 Python 和 Fortran 绑定
- 不提供 SST、DataMan、HDF5 和压缩算子
- 后续扩展可选能力前必须先按依赖项规则查重并确认依赖已发布
