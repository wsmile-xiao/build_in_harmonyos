# JerryScript 3.0.0 适配笔记

## 源码与构建

- 上游仓库：<https://github.com/jerryscript-project/jerryscript>
- 源码标签：`v3.0.0`
- 构建系统：CMake
- 设备源码归档 SHA256：`4d586d922ba575d95482693a45169ebe6cb539c4b5a0d256a6651a39e47bf0fc`
- 适配目标：HarmonyOS PC，clang/clang++
- 外部 Conan 依赖：无

配方关闭上游默认的 LTO 和 strip，保留 `shared`、`fPIC`、扩展、数学库、默认 port 和命令行工具选项；`UNITTESTS` 与 `DOCTESTS` 不进入发布包构建。

## W0 证据

- W0 预检 run：`20260909T142450Z-81634af8153e`
- 本地证据：`task-private/jerryscript-3.0.0/w0-evidence-r6/20260909T142450Z-81634af8153e/`
- 设备环境、主检出状态、源码归档、C 语言核心复核和 prescan 均通过。
- 语言复核：排除测试/工具等辅助目录后 580 个文件，C=269、C++=3，C/C++ 兼容族占 97.8%。
- prescan 记录了上游 Nuttx Makefile 的符号链接、开发工具 bash shebang、glibc 宏和 backtrace 规则命中；这些路径不进入默认 CMake 安装，设备原生构建无需补丁。

## 源码探测证据

- CMake/安装/测试布局 run：`20260909T142854Z-899607ac983b`
- 单元测试源码探测 run：`20260909T143124Z-5e1a6bd5f9d3`
- CMake 安装目标包含 `jerry-core`、`jerry-ext`、`jerry-port` 以及可选的 `bin/jerry`；`UNITTESTS=ON` 时生成独立的 `unit-*` 测试程序，不注册 CTest 用例。

## 测试约定

`test_package` 使用 Conan 生成的 `jerryscript::jerryscript` 目标，覆盖 `jerry_eval`、数值结果、扩展 print handler 和 `jerry --version`。正式设备构建、上游单元测试和 JS 测试结果以对应 W3 证据目录及报告为准。
