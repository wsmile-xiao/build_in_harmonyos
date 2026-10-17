# outcome 2.2.9 — 适配笔记（OHOS aarch64）

## 来源核验
- 官方仓库：https://github.com/ned14/outcome
- 正式标签：`v2.2.9`（git tag 指向 commit `571f9c930e672950e99d5d30f743603aaaf8014c`）
- 源码 tarball：`https://github.com/ned14/outcome/archive/refs/tags/v2.2.9.tar.gz`
- SHA-256：`2840e403b1d7a0d3a75ecc4df574ab0674284bb21d76ac5f817695f2b56905f2`（tarball 实测）
- 许可证：Licence.txt 双许可任选（Apache-2.0 OR CC-BY-4.0），按 ("Apache-2.0", "CC-BY-4.0") 申报
- 平台任务：7326（`outcome/2.2.9`，依赖活动 activity_id=6）

## 结构与 W0 依赖判定（关键）
- tarball 双形态：
  - `include/` 模块版（42 个 hpp）：**依赖未随 tarball 分发的 git 子模块** `quickcpplib`（config.hpp/import.h/execinfo_win64.h 及 Catch2 单元测试头）与 `status-code`（system_error2.hpp 等）
  - `single-header/` 自包含版：outcome.hpp / outcome-basic.hpp / outcome-experimental.hpp（按 `#include` 指令口径 grep 实证 0 处外部子模块依赖）
- W0 依赖实证：制品仓 `conan list quickcpplib/*` = 0 条；归档树无 quickcpplib、无 status-code → **R36：依赖未发布且子模块不可获得**
- 依上游 Readme/single-header/Readme.md，single-header 是官方打包的无依赖消费形态 → **本包交付 single-header 版**，include/ 模块版不打包（其依赖链 outcome→quickcpplib→status-code 每层均含 git 子模块，适配代价超出单包范围）
- C++17 消费（outcome 2.2 要求 C++17 起步）

## 分支基线说明
- 分支 `feat/outcome-2.2.9` 基于 fork `origin/main`（9b49d7903），理由同前（W3 JC6 原子性判定；fork main 为 upstream main 祖先，PR diff 不受影响）

## 上游测试（四维账本，如实申报）
- 上游测试套件：`test/tests/*.cpp` 共 **42 个 Catch2 测试文件**（comparison/constexpr/containers/core-outcome/core-result/hooks/issue00xx/experimental 等）
- **N_static（静态声明）= 42 个测试文件**（TEST_CASE 数因文件含多用例未逐宏展开，按文件级清点）
- **N_executed = 0**：42 文件中 41 个 `#include "quickcpplib/boost/test/unit_test.hpp"`、1 个（experimental-p0709a.cpp）直接依赖 status-code 模块头，quickcpplib/status-code 子模块不在 tarball 内、制品仓未发布 → **上游测试套件在本环境不可编译运行**（依赖缺失，如实申报，非适配缺陷）
- 运行尝试证据：`grep -rhoE "#include [<\"](quickcpplib|status-code)"` 实证 include/ 与 test/ 双双引用；探针编译 include/ 模块版路径未走（依赖缺失）
- 消费者测试 N_consumer = 1（5 项断言）

## 消费者 API 口径（试编译迭代确认）
- 单头版默认 policy 为 `fail_to_compile_observers`：`result<int, long>` 直接对非 error_code/exception_ptr 的 E（如 long）做宽观测器会 static_assert，**必须选用例别名 `unchecked<T,E>` 或 `checked<T,E>`**（官方指引，见报错信息原文）
- `success()`/`failure()` 显式构造糖在所有 policy 下可用
- 探针最终 5 项断言全过（unchecked value/error、checked error/value、string payload），clang++ -std=c++17，rc=0

## 路径 B 判断（结论：不走 B，纯路径 A）
- 零补丁、零上游修改；"tarball 自带 single-header 用于规避子模块依赖"是上游官方形态而非本适配独创知识。按纯路径 A 交付。

## test_package（消费者验证）
- Conan L1：CMakeDeps + find_package（C++17），消费者程序 `test_outcome.cpp` 链接打包 single-header
- 5 项断言：unchecked success(value/error 位)、unchecked error、checked error、checked value、checked string payload
- `test()` 经 bash 包装执行二进制（OHOS mksh 规避），退出码 0 判定通过

## 后续
- 状态：built（2026-09-12 finish 收尾）
- 无 commands.json（纯库，无命令行产物）

## 整改（2026-09-13，GLM-8；对应 rule4 驳回与人工审核意见"解决依赖后跑上游测试"）

### 依赖已解决（拓扑先行，独立任务）
- quickcpplib 0.1.0.0-gh0.20231208（任务 7384，PR #9872）：锁定自举期 master commit 72277c70f9；上游 20 测试 15 通过 + 5 平台受限如实申报；嵌套子模块 byte-lite/Optional/span-lite 按 .gitmodules pinned commit 以官方 tarball 补齐
- status-code 1.0-gh0.20240312（任务 7385，PR #9873）：锁定 outcome v2.2.9 官方 .gitmodules 子模块 commit a35d88d6；上游 5 测试 5/5 全通过
- 两个依赖版本锁定均与 outcome v2.2.9 官方子模块机制一致（兼容性有上游锁定背书）

### 配方改造
- 改打包 include/ 模块版头文件（不再用 single-header 替代），requirements() 声明上述两依赖；status-code 头按上游引用形态随包落位（include/outcome/experimental/status-code/include/status-code）
- build() 将 test/tests/ 42 个测试逐个编译运行（-std=c++17，-I 三方 include）

### 上游测试新账本（2026-09-14 真机实测）
- N_static = 42（文件级清点，口径与初版一致）
- N_executed = 42，**通过 42，test_skipped 0，未预期失败 0（100%）**
- 消费者测试 N_consumer = 1（test_outcome.cpp 5 断言，改链模块版 outcome.hpp，全过）
- 证据：reports/ 下 conan-create/w3 日志；逐文件 PASS 见构建日志
