# libxdiff

## 软件描述

libxdiff 是一个实现二进制和文本文件 diff 函数的库。它提供了文本差异比较、二进制差异比较、Rabin fingerprint 差异比较、三路合并等功能。

- **主页**: http://www.xmailserver.org/xdiff-lib.html
- **许可证**: LGPL-2.1-or-later
- **语言**: C/C++
- **构建系统**: autotools

## 主要功能

- 文本文件 diff/patch（类似 GNU diff/patch）
- 二进制文件 diff/patch
- Rabin fingerprint 二进制 diff
- 多段二进制 diff/patch
- 三路合并（merge3）

## API 概要

核心 API 定义在 `xdiff.h` 中：

- `xdl_diff()` — 文本差异比较
- `xdl_patch()` — 应用补丁
- `xdl_merge3()` — 三路合并
- `xdl_bdiff_mb()` — 二进制差异比较
- `xdl_init_mmfile()` — 内存映射文件初始化

## 已编译版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 0.23 | built | 2026-06-25 | HarmonyOS aarch64 平台适配，4 个补丁 |
