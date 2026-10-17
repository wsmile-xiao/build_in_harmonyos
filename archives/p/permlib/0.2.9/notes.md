# permlib 0.2.9 适配笔记

## 编译环境
- 构建系统: CMake（上游自带；本配方用 CMake 驱动上游测试）
- 编译日期: 2026-09-20
- 目标环境: OpenHarmony / HarmonyOS PC aarch64（HMK）
- 工具链: OHOS Clang 15.0.4、CMake 4.1.2（设备 `/data/service/hnp`）、Conan 2.29.1
- 状态: built
- 依赖: `boost/1.90.0.4.1`（公开头依赖；只用头文件，链接期零 boost 符号）

## 编译步骤

permlib 是**纯头文件库**：没有需要编译的库产物，配方的 `package()` 只把头
（`include/permlib/**`，84 个）和 LICENSE 装进包。因此本任务的"编译"由两件真实事情构成：

1. **上游测试套件的真实编译 + 运行**（配方 `build()` 内）：上游 `test/*.cpp` 是 13 个
   Boost.Test 可执行文件（每个自带 `BOOST_TEST_MODULE`），由配方自带的
   `files/CMakeLists.txt` 编译，注册进 ctest 后真实执行；语料 `data/`（39 个文件：37 个 `G_*` 图数据 + 2 个 `.pl` 辅助脚本）
   拷到构建根目录（上游用例用相对路径 `../data/...` 读取）。**上游源文件一字未改**
   （唯一改动是 5 个最小补丁，见下）。
2. **真实消费者编译 + 运行**（`test_package/`）：`find_package(permlib CONFIG REQUIRED)`
   → `permlib::permlib`，消费者 TU 只用公开头、自己**不写** boost 路径；断言 18 条，
   并跑两遍（conanrun 注入环境 + `env -u LD_LIBRARY_PATH` 裸环境）。

实际设备命令：

```bash
cd "$TARGET_REPO/archives/p/permlib/0.2.9"
conan create . \
  -pr:h="$TARGET_REPO/ci/conan/profiles/ohos-aarch64" \
  -pr:b="$TARGET_REPO/ci/conan/profiles/ohos-aarch64" \
  --build=missing -c tools.build:jobs=2
```

配方自限并行度（本机 affinity 8 而 conan 默认取 `cpu_count()`=20）：编译 `-j2`，
ctest `-j2`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试编译报多处 `no member named 'next' in namespace 'boost'` | Boost 1.90 起 `boost::next()`/`prior()` 的声明不再由 `boost/utility.hpp`、`boost/iterator/*` 等头间接引入；permlib 是 2011 年的 C++98 代码，依赖旧 Boost 的隐式包含 | 4 个使用点补 `#include <boost/next_prior.hpp>`（补丁 0002–0005），不引入任何平台宏 |
| 2 | `test-abstract-groups` 编译失败：`no matching constructor for initialization of 'AbstractBSGS<...>'` | 上游 `abstract_bsgs.h` 的 `setStabilizer()` 调用了**未声明**的「已算好 support」构造重载（第二个实参是 `boost::shared_ptr<std::set<dom_int> >`，而类里只有 `bool computeSupport` 版本）；模板方法不被实例化时不报错，属上游潜在缺陷 | 补一个语义等价的构造重载（补丁 0001）：`AbstractBSGS(bsgs_, support) : m_bsgs(bsgs_), m_support(support) {}` |
| 3 | 消费者编译期找不到 boost 头（若只写 `requires(..., transitive_headers=True)`） | boost 配方声明了 components ⇒ CMakeDeps 生成的**包级**目标 `boost::boost` 的 `INTERFACE_INCLUDE_DIRECTORIES` 为空，只有 `Boost::headers` 组件带 include | `package_info()` 写 `cpp_info.requires = ["boost::headers"]`（组件级），并用只 include 公开头的真实消费者验证 |
| 4 | 上游自带 `test/CMakeLists.txt` 无法在 Conan 下链接 Boost.Test | 它用 legacy 变量 `${Boost_UNIT_TEST_FRAMEWORK_LIBRARY}`，而 Conan 生成的 `BoostConfig.cmake`（CMakeDeps）只提供 imported target（`Boost::unit_test_framework`）；用 legacy 变量会让链接行退化成空，或 `find_package` 命中设备里其它 Boost 配置（假绿） | 配方自带 `files/CMakeLists.txt` 构建**同一批**上游源文件并注册 ctest；上游文件不改 |
| 5 | `tc.cache_variables` 注入的变量在上游 `project()` 之前读不到 | `cache_variables` 只进 CMakePresets/命令行，不进 `conan_toolchain.cmake` ⇒ 早读的变量静默退化成 fallback | 一律用 `tc.variables` 注入（`PERMLIB_SOURCE_DIR`、`CMAKE_SYSTEM_NAME`） |
| 6 | 测试可执行文件在 OHOS 平台上没有 build RPATH | OHOS profile 把 `CMAKE_SYSTEM_NAME` 设为 HarmonyOS，而本机 CMake 没有 `Platform/HarmonyOS-Initialize.cmake` ⇒ `UNIX` 变量不存在、RPATH 逻辑整支跳过 | 配方在 `generate()` 里对 Linux/OHOS 显式 `CMAKE_SYSTEM_NAME=Linux`（本仓 header-only 先例 array-hash 0.7.2 同法），测试可执行文件因此能直接跑 |

## 源码修改

`patches/` 共 5 个（`refresh-patch --auto` 的 per-file 形态，全部只动 `include/permlib/**`）：

| 补丁 | 修改 |
|---|---|
| `0001-include-permlib-abstract_bsgs.h.patch` | 补 `AbstractBSGS` 的 support 构造重载声明 + 定义（+11 行） |
| `0002-include-permlib-bsgs.h.patch` | 补 `#include <boost/next_prior.hpp>`（+1 行） |
| `0003-include-permlib-change-base_transpose.h.patch` | 同上（+1 行） |
| `0004-include-permlib-generator-schreier_generator.h.patch` | 同上（+1 行） |
| `0005-include-permlib-test-primitivity_sgs_test.h.patch` | 同上（+1 行） |

**没有任何平台宏**（无 `__OHOS__`、无平台分支）：这 5 处对任意平台都是同一份修正。
公共 API 与算法实现未改。

## 依赖版本

- `boost/1.90.0.4.1`：permlib 的 84 个公共头里 47 个直接 `#include <boost/...>`，
  因此 boost 是**接口依赖**（配方 `requires` + `cpp_info.requires = ["boost::headers"]`）。
  实测链接期零 boost 符号（消费者只 include 头），故 `transitive_libs=False`。
  选 1.90.0.4.1 的原因：它同时提供 `boost::headers` 组件与已编译的
  `libboost_unit_test_framework`，本仓既有 header-only 先例
  （array-hash/0.7.2、liborigin2/20110117）也用它。

## 验证结果

上游测试（Boost.Test，测试单位 = test case；13 个可执行文件 / 59 个 test case）：

```text
ctest --output-on-failure -j2       # 13/13 Passed，0 Failed
test-base 12 / test-trans 6 / test-generators 2 / test-partition 1 / test-permutation 7 /
test-search-setstabilizer 5 / test-symmetric-group 1 / test-search-matrixauto 1 /
test-orbit-lex-min 5 / test-api 5 / test-test 6 / test-export 2 / test-abstract-groups 6
= 59/59
```

消费者（鸿蒙特有测试）：`PERMLIB_CONSUMER_CHECKS 18/18`、`PERMLIB_CONSUMER_RESULT PASS`
（含裸环境 `env -u LD_LIBRARY_PATH` 一遍）。

逐字日志见 `reports/`（该目录被 `.gitignore` 覆盖，不进 PR）。

## 交付物

| 文件 | 说明 |
|---|---|
| `permlib/0.2.9` Conan 包 | header-only：`include/permlib/**`（84 个头）+ `licenses/LICENSE`；package_id 清空（`da39a3ee…`，无架构/编译器维度） |
| `archives/p/permlib/0.2.9/{conanfile.py,conandata.yml,manifest.yaml,notes.md}` | 配方与元数据 |
| `archives/p/permlib/0.2.9/test_package/` | 消费者测试（CMakeDeps 消费者 + 18 条断言 + 裸环境 smoke） |
| `archives/p/permlib/0.2.9/files/CMakeLists.txt` | 上游测试驱动（不改上游源文件） |
| `archives/p/permlib/{manifest.yaml,README.md}` | 软件级元数据 |

## 注意事项

- **boost 组件级传递是本包的关键口径**：写 `"boost::boost"`（包级）或只写
  `transitive_headers=True` 都会让消费者编译期找不到 boost 头；必须
  `cpp_info.requires = ["boost::headers"]`。知识草稿 `E629` 记录了完整判据与复现命令。
- 上游 `data/` 是测试语料（39 个文件：37 个 `G_*` + 2 个 `.pl` 辅助脚本），不是交付物，也不进包。
- 本例 `test_package` 的断言对照物全部在本文件外独立算出（闭式公式 `10!`、`4!·6!`、
  自写 BFS 暴力枚举、`SymmetricGroup` 另一条构造路径），不靠被测库自证。
