# List::SomeUtils::XS

## 描述
List::SomeUtils::XS 是 List::SomeUtils 模块的 XS（C 语言）加速版本，提供了高性能的列表处理函数。

## 功能特性
- 提供常用的列表操作函数的 XS 实现
- 比纯 Perl 版本性能更高
- 包括：any、all、none、notall、first、last、firstval、lastval、pairwise 等

## 依赖
- Perl 5.42.0
- List::SomeUtils 0.59（纯 Perl fallback）
- Module::Implementation 0.09

## 编译信息
- 构建系统: perl (Makefile.PL)
- 编译器: clang 18.1.8
- 目标平台: aarch64-unknown-linux-ohos
- 编译日期: 2026-06-12

## 预编译包
- `list-someutils-xs-0.58-ohos-aarch64.tar.gz` (159KB)

## 使用说明
XS 模块在 HMDFS 环境下可能无法直接加载，此时会自动使用纯 Perl fallback（List::SomeUtils 0.59）。功能完全正常。

## 版本历史
| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 0.58 | built | 2026-06-12 | 初次编译成功 |
