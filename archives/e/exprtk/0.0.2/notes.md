# exprtk 0.0.2 适配笔记

## 编译环境
- 构建系统: header-only（无构建；上游测试经 CMake 工具链门控编译）
- 编译日期: 2026-09-12
- 编译器: clang/clang++ 15.0.4（aarch64 OHOS 原生）
- 状态: built（W3 conan-verify 通过）

## 编译步骤

1. W0 preflight：零依赖，直接通过。
2. lang-preflight：detected=cpp（exprtk.hpp 单头 + 21 个 cpp 示例/测试；首跑因 --src 传空误判 perl，纠正源码目录后通过）。
3. conan-init 生成模板后按 header-only 检查清单重写：`package_type="header-library"`、`package_id()` clear、`generate()` 显式 CMakeToolchain、`package()` 只装 include/、无 libs（G3/G4/L2/L4/L5 全过）。
4. 上游测试门控选项 `run_upstream_tests`（默认 False，CI 与真机同一入口）：True 时生成最小 CMakeLists 到源码目录，CMake 工具链编译 exprtk_test.cpp（-O0 覆盖 release 优化）后直接运行。
5. 消费者测试 test.cpp：symbol_table/expression/parser 真实调用 API，6 项断言（表达式求值、变量重绑定重求值、min/max/pi 函数、非法表达式拒绝）。
6. 真机全量验证：`conan create -o 'exprtk/*:run_upstream_tests=True'`（profile ohos-aarch64）。

## 测试四维账本

| 维度 | 数值 | 说明 |
|---|---|---|
| 上游静态声明总数 N_static | 22 | exprtk_test.cpp main() 顺序调用 perform_test(numeric_type,00..21)，展开为 run_test00<numeric_type>()..run_test21<numeric_type>()，单一 double 类型 |
| 实际注册/可执行 N_registered | 22 | 全部纳入执行入口，无条件编译过滤 |
| 实际执行 N_executed | 22 | 真机 conan create 门控路径全量执行 |
| 通过/失败/跳过 | 22 / 0 / 0 | 修复后真机重跑逐条 SUCCESS，测试总耗时约 40.4 分钟（最慢 run_test14 516.3s、run_test19 448.9s） |
| 消费者测试 N_consumer | 1 | test_exprtk 程序，6 项断言（N_assertion=5），退出码 0 |

通过率口径：执行项 22/22；静态全量 22/22。上游无 runner 层（自写 main 直调），无跳过分类。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 误判 env_unsupported（perl 76%） | 调用脚本 find 路径失败导致 --src 传空，工具扫描了 builds 下其他项目目录 | 用真实源码目录 /storage/Users/currentUser/builds/exprtk-0.0.2.work 重跑，detected=cpp；tag 0.0.2 commit (2023-01-01) 即 C++ ExprTk |
| 2 | CMake.configure(src_folder=...) TypeError | 本环境 conan 版本的 CMake 助手不支持 src_folder 参数 | 改为生成 CMakeLists 到源码目录，configure()/build() 无参默认形态，self.run 直接运行测试二进制 |
| 3 | make jobserver mkfifo: Operation not permitted | HMDFS 不支持 jobserver fifo（MAKEFLAGS 环境） | 仅警告，构建继续，不影响结果 |
| 4 | W4 审计 P0：run_test14 空转通过 | run_test14 从进程 CWD 加载 exprtk_functional_test.txt（缺失时上游静默 return true）；conan build() 的 CWD 为构建目录，数据文件在源码目录，首轮该测试实际评估 0 条表达式（0.006s 空转） | build() 中以 conan copy 工具将两个 functional 数据文件复制到构建目录后运行；修复后重跑 run_test14 真实执行 516.34s 通过，22/22 全过 |

## 源码修改

无补丁（patches 为空，conandata.yml 显式 `patches: {}`，build() 显式调用 apply_conandata_patches）。

## 依赖版本

无依赖（header-only 单头库）。

## 验证结果

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -o 'exprtk/*:run_upstream_tests=True'
# 上游测试（W4 审计修复后真机重跑）：run_test00..run_test21 (double) 全部 SUCCESS
run_test00 118.45s / run_test01 344.91s / run_test02 331.45s / run_test03 75.27s
run_test04 19.35s / run_test05 20.68s / run_test06 0.88s / run_test07 153.85s
run_test08 36.77s / run_test09 41.70s / run_test10 157.07s / run_test11 6.37s
run_test12 121.63s / run_test13 21.19s / run_test14 516.34s / run_test15 0.12s
run_test16 0.57s / run_test17 0.33s / run_test18 1.68s / run_test19 448.88s
run_test20 5.08s / run_test21 0.75s
# 消费者测试：exprtk consumer test: all checks passed
# conan create 完整成功（含 test_package 运行）
```

## 注意事项

- exprtk 0.0.2 上游 Makefile 使用 `-c++`（g++ 别名）与 `-Werror`，设备无 c++/cc 别名，故测试编译走 Conan CMake 工具链（clang++），不依赖 shell 编译器变量（R33）。
- 上游测试用 -O0 覆盖 release 优化仅加速编译，语义不变；修复后全量 22 套件真机约 40 分钟，CI 默认选项跳过上游测试（消费者测试仍全跑）。
- exprtk.hpp 装至 include/ 根，消费者 `#include "exprtk.hpp"` 与上游使用习惯一致。
---

**编译结束**: 2026-09-12 05:00
**最终状态**: built
