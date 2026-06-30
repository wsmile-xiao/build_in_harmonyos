# LLVM 编译器基础设施

## 软件描述

LLVM是一套模块化、可重用的编译器和工具链技术。包括：

- LLVM核心库：提供现代源码和目标独立优化器，以及支持多种CPU架构的代码生成器
- Clang：C、C++、Objective-C和Objective-C++前端
- LLDB：调试器
- libc++：C++标准库实现
- compiler-rt：运行时库
- 各种工具：llvm-as、llvm-dis、opt、llc等

## 官方网站

- 项目主页：https://llvm.org/
- GitHub：https://github.com/llvm/llvm-project

## 特性

- 模块化设计
- 中间表示（IR）设计
- 支持多种前端和后端
- 强大的优化能力
- 支持JIT编译

## HarmonyOS适配说明

本预编译版本针对HarmonyOS进行了适配：

1. 添加了HarmonyOS平台识别（aarch64-unknown-linux-ohos）
2. 修改了HandleLLVMOptions.cmake支持HarmonyOS
3. 仅编译AArch64目标（减少编译时间）
4. 包含clang C/C++前端

## 使用建议

- clang-17位于bin/目录
- 库文件位于lib/目录
- 头文件位于include/目录
- 可用于编译C/C++程序