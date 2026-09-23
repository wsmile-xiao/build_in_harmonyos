# iec16022 for HarmonyOS

## 概述

iec16022 是一个 DataMatrix（IEC 16022 / ECC200）二维条码生成库，附一个命令行前端。
它把任意文本/二进制载荷编码为 ECC200 符号，并可直接输出 PNG、EPS、Hex、位图或纯文本。

## 功能

- `libiec16022`：ECC200 编码核心（`iec16022ecc200` / `iec16022ecc200f`）、
  Reed-Solomon 纠错（ISO/IEC 16022 Annex R 算法）、PNG 图像渲染。
- `bin/iec16022`：命令行工具，支持 `-c/--barcode`、`-i/--infile`、`-o/--outfile`、
  `-f/--format`（Text/UTF-8/EPS/PNG/Bin/Hex/Stamp）、`-s/--size`、`-e/--encoding`、
  `--gs1` 等选项。
- 自动选择最小的、能容纳载荷的 ECC200 符号尺寸，也可用 `-s WxH` 指定。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | iec16022 |
| 上游 | https://github.com/rdoeffinger/iec16022 |
| 许可证 | GPL-2.0-or-later |
| 构建系统 | autotools |
| 语言 | C |

## OHOS 适配

- `config.guess` / `config.sub` 需要补丁才能识别 HarmonyOS；
  `config.guess` 会输出 `aarch64-unknown-linux-ohos`，`config.sub` 需同时接受
  `ohos-linux` 三元组与 `linux-ohos` kernel-OS 组合。
- autoconf 的临时目录创建使用 `umask 077`，在 HMDFS 的 setgid 目录语义下会
  产生属主不可写的目录，需放宽 umask。
- 官方 release asset（`iec16022-0.3.1.tar.xz`）自带生成的 `configure` 与
  `Makefile.in`，无需 `autoreconf`；GitHub 的 git-archive tarball 则不含，需注意区分。
- 上游测试依赖随源码发布的参考产物做逐字节比对，可在设备上完整执行。

## 依赖关系

| 依赖 | 类型 | 说明 |
|------|------|------|
| popt | 运行时（静态） | 命令行选项解析，configure.ac 硬性要求 |

zlib 不是依赖：源码中 `image.c` 的 zlib 分支由 `#ifdef USEZLIB` 控制，上游默认关闭
（PNG 的 IDAT 使用自实现的未压缩 deflate 块）。

## 参考资料

- 上游仓库: https://github.com/rdoeffinger/iec16022
- IEC 16022 标准: ISO/IEC 16022 (Data Matrix)
