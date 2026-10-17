# libecpint 1.0.7 适配笔记（HarmonyOS PC / OHOS aarch64）

- 上游：https://github.com/robashaw/libecpint （release v1.0.7 tag 归档）
- 源码 sha256：`e9c60fddb2614f113ab59ec620799d961db73979845e6e637c4a6fb72aee51cc`
- 构建系统：CMake ≥ 3.12（C++11，C 亦启用）；本任务 recipe 走 `CMakeToolchain` + `CMakeDeps`
- 平台积分赛任务：ohpcd 任务 8171（分支 feat/libecpint-1.0.7，medium）

## R51 上游测试三步法

> 计数口径（R2 修订）：单元测试按 gtest 用例（TEST/TEST_F/TEST_P 宏实例）计；
> 集成测试按独立可执行程序计。R1 的"可执行测试项 18"口径被外部审查判少报
> （gtest 用例实测 53），已全套改为用例级口径。

### 第一步：清点（适配前，基于 v1.0.7 源码归档）

| 套件 | 数量 | 计量基准 | 明细 |
| --- | --- | --- | --- |
| tests/units | 53 | gtest 宏实例 | mathutil 7、multiarr 13、bessel 7、gshell 8、ecp 11、generate 3、gaussquad 4 |
| tests/lib | 10 | 独立程序 | IntTest1、IntTest2、DerivTest1、DerivTest2、HessTest1、HessTest2、APITest1、APITest2、Type1Test1、Type1Test2，benchmark 对照 `*.output`（check_file 阈值 1e-5） |
| tests/lib/stress_test | 1 | 独立程序 | `StressTest` 自定义目标 POST_BUILD 执行，argv 传 `share/libecpint` |
| **合计（上游测试用例 N）** | **64** | 53 用例 + 11 程序 | ctest 注册 17 项（gtest 用例聚合于 7 个程序内，stress 不注册） |

参数化披露：gaussquad 4 个 TEST_P × 2 组参数（Values(CreateBigGrid, CreateSmallGrid)）
实跑展开为 8 个实例，7 个 gtest 程序实跑共 57 个运行实例。

上游无 pytest / make check；docs（LIBECPINT_BUILD_DOCS 默认 ON）需 Sphinx/Doxygen，不属测试。

### 第二步：实跑（本任务在 OHOS aarch64 设备原生执行）

- 执行路径：conan create → build() → `cmake.build()`（含全部测试二进制）→ `cmake.build(target=StressTest)`（POST_BUILD 实跑压测）→ `cmake.test()`（ctest 17 项，`--output-on-failure`）。
- 证据：conan create 日志（含 `Test project`、`100% tests passed` 与两个 HMBS_*_TEST_RESULT 标记），保存于任务 evidence/。
- 逐项结果：ctest 17/17 过（覆盖 10 个 benchmark 程序 + 53 个 gtest 用例，gtest 任一用例失败会使程序非零退出）；StressTest 过。合计 N=64，N′=64，通过 64，失败/跳过 0。

### 第三步：PR 回填

- 上游 N=64（53 gtest 用例 + 11 独立程序），N′=64，通过 64。
- test_package 消费者测试 4 组断言（计入鸿蒙特有测试，不进上游分母）。

## 适配要点

1. **依赖收敛（补丁 0001/0002）**：上游 `external/ImportPugiXML.cmake` / `ImportGTest.cmake` 均为"系统 find_library → 配置期网络拉取"两级回退，clean 环境不可靠。整体替换为 `find_package(pugixml CONFIG REQUIRED)` / `find_package(gtest CONFIG REQUIRED)`，并保留上游期望的目标名（`libpugixml` / `gtest`）作 ALIAS，src 与 tests 的 CMake 零改动。补丁不含平台宏（R8/PF5）。
2. **依赖版本**：pugixml/1.15-r0、gtest/1.17.0（W0 实测制品仓均可 download）。gtest 仅 test_requires；其包只提供 gtest::gtest 组件，与上游单测自带 main() 正好匹配。Eigen 为上游 example 的可选项（未参与构建），**不是**本包依赖；cerf 保持 OFF 走内置 Faddeeva。
3. **构建期代码生成**：`generate` 可执行程序 + makelist.py（Python）在构建机原生执行（OHOS worker 即 aarch64 原生环境，无交叉执行问题）。recipe 用 `shutil.which("python3")` 显式钉住 `Python_EXECUTABLE`（R33：不依赖裸 shell 变量），避免 FindPython 搜索失败。
4. **docs 关闭**：`LIBECPINT_BUILD_DOCS=OFF`（上游默认 ON，需 Sphinx/Doxygen，CI 无此能力）。
5. **安装内容**：头文件（含生成的 config.hpp）、`libecpint`（SOVERSION 1）、内置 `Faddeeva` 库、`share/libecpint` 数据、CMake config/targets。cpp_info.libs 同时声明 `ecpint` 与 `Faddeeva`（静态消费需要）；`resdirs=["share"]` 供下游定位基组数据。`generate` 工具不安装 → 纯库包，无 commands.json（R38）。
6. **测试运行语义**：`cmake.test()` 失败即抛错；HMBS_UPSTREAM_TEST_RESULT / HMBS_STRESS_TEST_RESULT 标记只在真实通过后输出（防止把未跑当通过）。stress 失败会使构建步骤本身失败（POST_BUILD 语义）。
7. **/tmp 只读（E002）**：沿用 lodepng 的 `_pin_writable_tmpdir` 模式，构建/运行前把 TMPDIR 钉到可写目录。

## 已知限制

- 上游 `example/`、`doc/` 未接入（根 CMakeLists 不构建 example；docs 被显式关闭）。
- gaussquad 为参数化 gtest（TEST_P）：源码 4 个实例 × 2 组参数实跑展开为 8 个运行实例；
  PR 表格按"上游测试用例 64 = 53 gtest 用例 + 11 独立程序"口径统一，运行实例只作明细披露。
