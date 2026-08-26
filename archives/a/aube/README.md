# aube

Aube is a fast Node.js package manager.

## 描述

aube 是一个快速 Node.js 包管理器，使用 Rust 编写，支持 pnpm/npm/yarn 生态的多种锁文件与工作流。

## 已编译版本
- 1.32.0 (2026-08-25)

## 构建系统

cargo (Rust workspace)

## 依赖
- Rust/cargo 工具链
- clang 链接器（OHOS target）

## 特性
- 快速 Node.js 包管理
- 支持多种锁文件格式
- 提供 `aube` 命令行入口

## 使用方法
```bash
aube --version
aube install
aube run
```

## 注意事项
- 需要 Rust 工具链和 aarch64-unknown-linux-ohos target
- 编译时如无网络会使用空 primer，运行时按需回退到网络获取包元数据
