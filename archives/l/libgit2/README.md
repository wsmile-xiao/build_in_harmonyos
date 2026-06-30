# libgit2

libgit2 是一个轻量级、跨平台的 Git 核心库实现，提供可链接的 Git 库，无需依赖 Git 二进制文件。

## 描述

libgit2 是一个纯 C 实现的 Git 核心方法库，设计为可移植、高性能且跨平台。它提供了 Git 的核心功能，包括：

- 仓库操作（创建、克隆、打开）
- 提交、树和对象操作
- 引用管理（分支、标签）
- 索引和工作目录操作
- 网络传输（HTTP、SSH、Git 协议）
- 合并和变基操作

## 编译版本

- **1.9.0** (2026-05-19)

## 依赖

- OpenSSL (HTTPS 支持)

## 编译选项

- 构建系统: CMake
- HTTPS 后端: OpenSSL
- 编译器: Clang 15.0.4

## 相关链接

- 官方网站: https://libgit2.org/
- GitHub: https://github.com/libgit2/libgit2