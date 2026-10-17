# console-bridge 1.0.1 适配笔记

## 编译环境

- 构建系统：CMake
- 编译日期：2026-09-08
- 编译器：Apple Clang 17（本机配方预验证）
- 目标平台：HarmonyOS PC arm64
- 状态：built；HarmonyOS PC W3 待远端 worker 验证

## 源码与依赖

- 官方源码：`https://github.com/ros/console_bridge/archive/refs/tags/1.0.1.tar.gz`
- SHA256：`2ff175a9bb2b1849f12a6bf972ce7e4313d543a2bbc83b60fdae7db6e0ba353f`
- 第三方运行依赖：无
- 构建工具：CMake、C/C++ 编译器、Python 3（上游测试配置阶段）

## 构建与适配

上游源码无需修改。Conan 配方完成以下构建层适配：

1. 为 CMake 4 通过 cache 参数传入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`。
2. `os=OHOS` 时显式使用 `CMAKE_SYSTEM_NAME=OHOS` 与 `aarch64`，确保共享库生成正确 SONAME。
3. 非系统同名库按仓库规则默认构建共享库，并保留 `shared=False` 选项。
4. 固定安装到 `lib/`，声明实际库名 `console_bridge` 及 CMake/pkg-config 元数据。
5. 禁用依赖联网下载的 cppcheck/cpplint 辅助项，保留并执行全部 13 个功能测试用例。

## 测试基线

- 上游测试源：`test/console_TEST.cc`
- 上游 GoogleTest 用例：13 个
- CTest 注册的功能测试程序：1 个（`console_TEST`）
- 可选 lint 项：2 个；仅在找到 wget 时注册，且会在构建时联网下载脚本，因此配方中禁用
- 本机原始上游测试：1/1 CTest 通过，内部 13/13 GoogleTest 用例通过
- Conan 消费者测试：9 项真实行为断言通过

消费者测试覆盖日志格式化与转发、四级别映射、阈值过滤、日志级别读取以及输出处理器恢复。

## 已知限制

当前工作机为 macOS，不能用本机结果冒充 HarmonyOS PC W3。本分支只记录本机原始测试和 Conan 配方预验证结果，最终 HarmonyOS PC 结果以远端 worker/CI 日志为准。
