# 7zip 25.01 适配笔记

## 编译环境
- 构建系统: makefile (自定义 Makefile)
- 编译日期: 2026-04-24
- 编译器: clang / clang++
- 状态: success

## 编译步骤
- 源码解压后直接 `make CXX=clang++ CC=clang`，无 configure 步骤
- 安装通过手动复制 7z 二进制到目标目录

## 遇到的问题与解决方案
无重大问题。

## 依赖版本
无外部依赖（自包含构建）。

## 注意事项
- 25.01 版本引入了 Rust 代码，需通过 DISABLE_RUST=1 禁用
- Rust 支持未启用，部分新特性可能不可用
