# lldb

LLVM 项目调试器（llvm-project monorepo 的 lldb 组件）。本仓库适配 llvm-project 22.1.0 standalone lldb 树到鸿蒙 PC（arm64）平台，Conan 配方管理。

## 说明
- 官方源：https://github.com/llvm/llvm-project （llvmorg-22.1.0 release，standalone lldb 树）
- 构建系统：CMake + Ninja（llvm/22.1.0 配方 clang 工具链）
- 依赖：llvm/22.1.0、clang/22.1.8、libedit/20240808（均已发布制品仓）
- 产物：liblldb 动态库 + lldb/lldb-server 命令行工具 + SB API 头（include/lldb/API）
- 测试基线（R51 全量实测，详见 0.0.1/notes.md 台账）：lit 33638 用例 94.52% pass / gtest 31387 用例 99.91% pass / API 套件 1342 100%；失败全部归因于 host 沙箱（ptrace/EPERM）或上游固有缺陷，零适配缺陷

## 版本索引
| 版本 | 状态 | 备注 |
|------|------|------|
| 0.0.1 | published | 首次鸿蒙 PC 适配（2026-09-27，8 补丁 + test_package 实质 SB API 测试） |
