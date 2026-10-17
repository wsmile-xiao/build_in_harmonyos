# DRAFT-ohos-cmake-add-test-target-file

> 草稿知识项 — CTest add_test 测试可执行文件路径定位（$<TARGET_FILE:> 生成器表达式）
> 来源：blitz 1.0.2 适配（feat/blitz-1.0.2，2026-09-08）
> 同 stem 配对：`knowledge/drafts/DRAFT-ohos-cmake-add-test-target-file.kv`

## 问题（现象 / error_signature）

- 上游 `cmake/UnitTests.cmake` 用 `add_test(${exec} ${TEST_PATH}/${exec})` 注册 CTest，测试可执行文件路径被硬编码为 `${TEST_PATH}/${exec}`。
- 当 `RUNTIME_OUTPUT_DIRECTORY` 被改写（如 `Win32Compat.cmake` 把输出目录设成 `${CMAKE_BINARY_DIR}/src`）、构建目录布局变化、或使用 multi-config 生成器时，`ctest` 运行时无法按硬编码路径定位测试二进制，表现为测试找不到 / 目录缺失。
- OHOS/Conan 交叉构建环境对输出目录的处理与上游默认假设不一致，硬编码路径问题被放大。

## 根因（root_cause）

1. `add_test(<name> <command> ...)` 的 `<command>` 若写死为 `${TEST_PATH}/${exec}`，则把"测试二进制在哪"这个本应由 CMake 生成期决定的问题提前固化到配置期路径字符串里。
2. 构建目录布局（`CMAKE_BINARY_DIR` 结构、multi-config 的 `Debug/Release` 子目录、`RUNTIME_OUTPUT_DIRECTORY` 覆盖）变化后，硬编码路径与真实产物位置脱节。
3. CMake 提供 `$<TARGET_FILE:${target}>` 生成器表达式，在**生成期**解析目标的实际产物路径，天然跟随输出目录设置，无需人工维护路径拼接。

## 可复用方案（rec_approach: generator-expression-target-file-for-add-test）

将上游测试注册从硬编码路径改为目标名生成器表达式：

```cmake
# 上游（问题）
add_test(${exec} ${TEST_PATH}/${exec})
# 修复
add_test(NAME ${exec} COMMAND $<TARGET_FILE:${target}>)
```

- 若测试目标由宏/函数内联创建（blitz 的 `UnitTests.cmake` 即如此），函数内已有 `${target}` 变量，直接引用即可，无需把 `${TEST_PATH}` 传进注册逻辑。
- 与 `BLITZ_BUILD_EXAMPLES/BENCHMARKS` 子开关配合，可只跑 testsuite（`BUILD_TESTING=ON` 下 `BLITZ_BUILD_EXAMPLES=OFF/BLITZ_BUILD_BENCHMARKS=OFF`）而不牺牲 CTest 结果（blitz 57/57）。

## 适用条件

- 上游 CMake 用 `${TEST_PATH}/${exec}` 或 `${CMAKE_BINARY_DIR}/.../${exec}` 硬编码注册 `add_test` 的库；
- 构建会改写 `RUNTIME_OUTPUT_DIRECTORY` / 使用 multi-config 生成器 / OHOS、Conan 交叉构建输出目录与上游假设不一致。

## 反例（不适用场景）

- 上游已用 `add_test(NAME xxx COMMAND ${target})`（直接传目标名、CMake 自动解析）或 `catch_discover_tests` 等自动发现机制时，无需再改；
- 测试二进制固定输出到默认目录、且不跨生成器/不覆盖输出目录的纯本地常规项目。

## 验证证据（真实命令 + 结果）

- blitz 补丁 `0001-cmake-testsuite-only.patch` 将 `add_test(${exec} ${TEST_PATH}/${exec})` 改为 `add_test(NAME ${exec} COMMAND $<TARGET_FILE:${target}>)`；
- 本地 `conan create` 构建通过，test_package 断言 PASS 4/4；
- OHOS aarch64 构建记录 CTest 57/57（notes.md，2026-08-05 已通过）。

## 限制与恢复条件

- `$<TARGET_FILE:${target}>` 要求 `${target}` 必须是已定义的 CMake 目标名，且位于同一目录作用域（或全局目标）；跨子目录需 `add_test` 在目标定义处注册或确保目标可见。
- 恢复条件：若上游后续改用自动测试发现（catch_discover_tests / gtest_discover_tests），可移除本补丁；否则保留生成器表达式写法。

## 相关既有条目差异化定位表

| 既有条目 | 问题层 | 与本条差异 |
|---|---|---|
| E459（mysql 客户端库语义剪枝） | 交叉构建中裁剪服务端特性/辅助目标，`TARGET_FILE` 用于解析**构建工具**路径 | 本条的 `$<TARGET_FILE:>` 专用于 **CTest add_test 测试可执行文件路径定位**，不涉及库目标图剪枝 |
| DRAFT-ctpg（catch2 模块注入） | 手写 `add_test(NAME ${TARGET} COMMAND ${TARGET})` 替代 catch_discover_tests 模块 | 其 COMMAND 直接传目标名依赖 CMake 默认解析；本条针对上游**硬编码 `${TEST_PATH}` 路径字符串**这一具体失效模式，用生成器表达式显式解析产物路径 |
| DRAFT-cpplocate（test_package 可靠性） | test_package 中 CHECK 宏 + 前置条件 + 纳入 `add_test` 自动化 | 其 `add_test(NAME test_<lib>_hmos COMMAND test_<lib>_hmos)` 是 test_package 场景；本条是**上游源码 CMake 的测试注册路径定位**，作用位置不同 |
| DRAFT-ctre（header-only test_package） | test_package 缺 `include(CTest)/add_test` 导致 `cmake.test()` 无目标 | 是"缺注册"；本条是"注册了但路径硬编码失效"，互补不重叠 |
| DRAFT-isutf8（configure 期 file(DOWNLOAD)） | configure 期外网下载 benchmarks 需选项守卫 | 与本条无关（不同阶段不同根因），仅同属"CMake 选项补丁"大类 |

## 查重记录

- 全库 `grep -niE 'add_test|TARGET_FILE|TEST_PATH|generator|生成器表达式' index.tsv graph/*.kv drafts/*.kv`：
  - `add_test` 出现于 E239/E417、DRAFT-ctpg/cpplocate/ctre，均为不同问题层（见上表）；
  - `TARGET_FILE` 仅 E459（构建工具解析）与 E077（签名脚本变量，无关）；
  - `TEST_PATH` 组合、`$<TARGET_FILE:${target}>` 用于 add_test 的写法：**0 命中**。
- 结论：问题层（add_test 硬编码路径 → 生成器表达式定位）为真增量，可申报路径B。
