# TCL (Tool Command Language)

## 简介
TCL 是一种动态编程语言，由 John Ousterhout 创建。它被设计为一种简单但强大的脚本语言，常用于快速原型开发、脚本编写、GUI 开发（通过 Tk）和测试自动化。

## 主要特点
- 简洁的语法，易于学习和使用
- 跨平台支持（包括 HarmonyOS）
- 可扩展性强，可通过 C/C++ 扩展
- 内置强大的字符串处理功能
- 支持 OOP（通过 TclOO）

## 编译版本
- **8.6.14** (2024-02-24) - 最新稳定版本

## 编译信息
- 构建系统: Autotools
- 编译器: Clang
- 平台: HarmonyOS HongMeng Kernel 1.12.0

## 安装产物
- tclsh8.6 - TCL shell 解释器
- libtcl8.6.a - TCL 静态库
- libtclstub8.6.a - TCL stub 库（用于扩展开发）

## 使用示例
```tcl
#!/usr/bin/tclsh8.6
puts "Hello from TCL!"
puts [info patchlevel]
```

## 依赖关系
TCL 通常不需要外部依赖，但在某些平台上可能需要：
- zlib（可选，用于压缩支持）

## 相关链接
- 官网: https://www.tcl.tk/
- 文档: https://www.tcl.tk/man/
- 源码: https://sourceforge.net/projects/tcl/
