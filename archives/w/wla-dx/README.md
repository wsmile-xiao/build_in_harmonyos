# wla-dx 10.6

**Yet another crossassembler package** — 多架构交叉汇编器工具集

## 概述

wla-dx 是一套支持多种 CPU 架构的交叉汇编器包，包含汇编器、链接器和库文件管理工具。

## 支持的架构

- GB-Z80 (Game Boy Z80)
- Z80 / Z80N
- 6502 / 65C02 / 65CE02
- 65816
- 68000 / 6800 / 6801 / 6809
- 8008 / 8080
- HUC6280
- SPC-700
- SuperFX

## 构建信息

| 项目 | 值 |
|------|-----|
| 版本 | 10.6 |
| 构建系统 | CMake |
| 许可证 | GPL-2.0-or-later |
| 语言 | C |
| 平台 | OpenHarmony (aarch64) |
| 编译器 | clang 15.0.4 |
| 依赖 | 无 |
| 状态 | published |

## 产物

18 个二进制文件安装到 `bin/` 目录:

| 工具 | 说明 |
|------|------|
| wla-gb | Game Boy Z80 汇编器 |
| wla-z80 | Z80 汇编器 |
| wla-z80n | Z80N 汇编器 |
| wla-6502 | 6502 汇编器 |
| wla-65c02 | 65C02 汇编器 |
| wla-65ce02 | 65CE02 汇编器 |
| wla-65816 | 65816 汇编器 |
| wla-68000 | 68000 汇编器 |
| wla-6800 | 6800 汇编器 |
| wla-6801 | 6801 汇编器 |
| wla-6809 | 6809 汇编器 |
| wla-8008 | 8008 汇编器 |
| wla-8080 | 8080 汇编器 |
| wla-huc6280 | HUC6280 汇编器 |
| wla-spc700 | SPC-700 汇编器 |
| wla-superfx | SuperFX 汇编器 |
| wlab | 二进制到 WLA DB 转换器 |
| wlalink | WLA DX 链接器 v5.21 |

## 安装

```bash
# 通过 Conan 安装
conan install --requires=wla-dx/10.6@ohpcd/stable -pr:h=ohos-aarch64
```

## 已知限制

- wla-* 系列汇编器在 OpenHarmony 上因 /tmp 只读无法完成汇编操作（临时文件创建失败）
- wlalink 和 wlab 可正常使用
- 编译必须使用 `make -j1`（避免 HMDFS mkfifo 问题）

## 源码

- 主页: https://github.com/vhelin/wla-dx
- 下载: https://github.com/vhelin/wla-dx/archive/refs/tags/v10.6.tar.gz
- SHA256: `010c4d426fd1733b978cbca7530a5e68bdfb6f62976c0d5ff7bff447894e19a8`
