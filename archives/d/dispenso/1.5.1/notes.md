# Dispenso 1.5.1 HarmonyOS 适配笔记

## 编译环境

- 构建系统: CMake 4.2.3 + Ninja 1.13.2
- 编译日期: 2026-09-10
- 编译器: OHOS Clang/Clang++ 15.0.4
- 目标: HarmonyOS 6.0 aarch64
- 状态: built

## 编译步骤

Conan 下载并校验官方 `v1.5.1` 源码，使用 OpenHarmony SDK 的
`aarch64-linux-ohos` 工具链配置 CMake。构建阶段启用上游测试，关闭示例、
benchmark 与实验性 fast_math；GoogleTest 由 `test_requires` 提供，构建期间
不执行在线拉取。上游测试通过后安装库、头文件、许可证与 CMake 配置文件，
最后构建并运行独立消费端测试。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `-Werror` 使编译中止 | OHOS SDK 工具链注入 `--gcc-toolchain`，Clang 报 `unused-command-line-argument` | 仅添加 `-Wno-error=unused-command-line-argument`，保留其他警告升级 |
| 2 | 上游测试在无网络构建环境会尝试 FetchContent | CMake 未找到 GTest 时会回退到 GitHub 下载 | 通过 Conan `test_requires("gtest/1.17.0")` 和 `GTest_DIR` 使用已发布包 |
| 3 | 初次消费端编译找不到 `moodycamel/concurrentqueue.h` | Conan 生成目标默认只导出 `include`，而上游目标还有第二个公开包含目录 | 在 `cpp_info.includedirs` 中同时导出 `include/dispenso/third-party` |
| 4 | 共享库的 pipeline 异常安全用例持续自旋 | 异常指针与递归深度 TLS 分别在不同共享模块处理，Clang 跨 DSO 捕获或重抛可能失效，且模块可能观察到不同 TLS 状态 | 回移上游提交 `68b6dc3` 与 `3a1aaa4`，并让头文件实现的 pipeline 在调用方模块重抛已捕获异常 |
| 5 | 官方 profile 下 HarmonyOS 专项测试未注册 | 本地 Conan 将 OHOS 的 CMake 系统名映射为 `Linux`，仅检查 `CMAKE_SYSTEM_NAME` 会漏测 | 由 test_package 配方根据 `settings.os=OHOS` 显式传递 `DISPENSO_TEST_OHOS` |

## 源码修改

未修改任何上游测试用例。应用 2 个上游官方回移补丁和 1 个通用可移植性补丁：

- `patches/0001-capture-exception-at-catch-site.patch`：来自上游提交
  `68b6dc3189646669dce17573fa91bb3d671ea863`，修正 Clang 共享库跨模块
  异常捕获与空 `exception_ptr` 重抛问题。
- `patches/0002-unify-pipeline-inline-depth.patch`：回移上游提交
  `3a1aaa4056474061994a423179573719d58cd3c6` 中的 pipeline 相关修改，
  将递归深度 TLS 统一到库内并通过导出访问器访问。
- `patches/0003-rethrow-pipeline-exceptions-in-caller.patch`：保留现有公开
  `wait()` 行为，并让头文件实现的 pipeline 从库中取回 `exception_ptr` 后在
  调用方模块重抛，避免共享库运行时跨模块重抛失效。

## 依赖版本

- 生产依赖: 无第三方 Conan 包；使用系统 Threads。
- 测试依赖: `gtest/1.17.0`。
- 内嵌实现: 上游随源码提供 moodycamel concurrentqueue。

## 验证结果

```text
上游测试用例清点: 1109 项（全部源码保留，未修改或删除）
上游官方自动化套件: 1080/1080 通过（100%）
独立消费端测试: 1/1 通过，16/16 运行时检查通过（100%）
HarmonyOS 专项测试: 1/1 通过，5/5 运行时检查通过（100%）
```

上游把 `priority_test.cpp` 和 `timed_task_test.cpp` 的 19 项测试显式标记为
`flaky`，并在官方自动化主流程中排除；另有 10 项未由上游稳定配置实例化
或注册（包括明确未接入 CMake 的 `shared_pool_test.cpp`）。本适配严格执行
同一 1080 项稳定测试集合，完整保留清点出的 1109 项上游测试源码。

## 交付物

Conan 包包含静态或共享 `dispenso` 库、全部稳定公开头文件、上游 CMake 包
配置及 MIT 许可证；仓库不保存编译产物或下载缓存。

消费端测试还覆盖 `TaskSet::wait()` 的异常重抛、串行 pipeline 阶段异常在
调用方模块的精确重抛，以及 96 项串行 pipeline continuation 在达到 32 层
内联上限后仍完整执行，从而直接验证三个异常与深度保护补丁。

## 注意事项

默认生成静态库；消费者使用 `find_package(Dispenso CONFIG REQUIRED)` 和
`Dispenso::dispenso`。共享构建可通过 Conan 的 `shared=True` 选项启用。

## 最终状态

HarmonyOS 6.0 aarch64 的静态库、共享库、上游稳定测试套件、独立消费端
测试和 HarmonyOS pthread 专项测试均已通过，归档状态为 `built`。
---

**编译结束**: 2026-09-10 14:36
**最终状态**: built
