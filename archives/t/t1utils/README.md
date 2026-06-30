# t1utils

**分类**: 文件操作类
**许可证**: MIT
**Homepage**: https://www.lcdf.org/type/

## 简介

t1utils 是一组用于处理 PostScript Type 1 字体的命令行工具。它们可以在 PFA（ASCII 格式）、PFB（二进制格式）、人类可读描述格式和 Macintosh 格式之间相互转换 Type 1 字体。

## 工具列表

| 工具 | 功能 | 输入格式 | 输出格式 |
|------|------|---------|---------|
| t1ascii | PFB 转 PFA | PFB (binary) | PFA (ASCII) |
| t1binary | PFA 转 PFB | PFA (ASCII) | PFB (binary) |
| t1asm | 可读描述转 PFA/PFB | 人类可读描述 | PFA/PFB |
| t1disasm | PFA/PFB 转可读描述 | PFA/PFB | 人类可读描述 |
| t1unmac | Mac 字体转 PFA/PFB | MacBinary/AppleSingle/AppleDouble/BinHex | PFA/PFB |
| t1mac | PFA/PFB 转 Mac 字体 | PFA/PFB | MacBinary/AppleSingle/AppleDouble/BinHex |

## 已编译版本

| 版本 | 状态 | 日期 | 补丁数 |
|------|------|------|--------|
| 1.42 | published | 2026-06-12 | 3 |

## 依赖

无外部依赖。t1utils 是纯 C 命令行工具集合。
