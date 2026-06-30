# cmix

## 软件信息

| 字段 | 值 |
|------|-----|
| 名称 | cmix |
| 描述 | Data compression program with high compression ratio |
| 主页 | https://www.byronknoll.com/cmix.html |
| 许可证 | GPL-3.0-or-later |
| 语言 | C/C++ |
| 构建系统 | Makefile（纯 Makefile，非 autotools） |
| 依赖 | 无外部依赖 |

## 简介

cmix 是一款无损数据压缩程序，旨在优化压缩比，代价是高 CPU/内存使用。由 Byron Knoll 开发，使用混合上下文模型（包括 PAQ8、PPMd、LSTM 神经网络和 SSE）实现极高的压缩率。

运行时建议至少 32GB RAM。

## 已编译版本

| 版本 | 状态 | 编译日期 | 编译器 | 补丁数 |
|------|------|---------|--------|--------|
| 21 | built | 2026-06-25 | clang++ 15.0.4 (aarch64) | 2 |

## 版本 21 适配说明

cmix v21 原始 makefile 硬编码 `CC = clang++-17`，在鸿蒙平台上改为 `CC = clang++`。
源码中 `src/models/fxcmv1.cpp` 直接 `#include <immintrin.h>`（x86 专用头文件），需用 `#if defined(__x86_64__) || defined(__i386__)` 守卫，aarch64 走标量回退分支。

详见 `21/notes.md`。
