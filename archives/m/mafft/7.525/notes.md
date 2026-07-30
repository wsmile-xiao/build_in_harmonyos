# mafft 7.525 — HarmonyOS PC 适配笔记

## 软件概述
MAFFT（Multiple Alignment using Fast Fourier Transform）是多序列比对工具，支持
蛋白质/DNA/RNA 序列的快速与高精度比对。核心为纯 C 实现，使用 FFT 加速相似度计算，
支持多线程（-lpthread）。主入口 `mafft` 为 bash 脚本，按算法策略分派到 libexec/mafft/
目录下的内部二进制程序。

## 源码来源
- 上游官网：https://mafft.cbrc.jp/alignment/software/
- 源码包：`mafft-7.525-without-extensions-src.tgz`（BSD-3-Clause，不含 RNA 扩展）
- 解压后顶层目录：`mafft-7.525-without-extensions/`
- 核心源码与 Makefile 位于 `core/` 子目录

## 编译环境
- 构建系统：makefile（plain make，core/Makefile）
- 编译日期：2026-07-17
- 编译器：clang（通过 Conan conf 获取，R33）
- 状态：built

## 编译步骤
1. `source()` 下载并解压源码包（strip_root=True 去除顶层目录）
2. `build()`：
   - `apply_conandata_patches` 应用 0001-mafft-relocatable-libdir.patch（将 mafft.tmpl
     中的 `_LIBDIR` 替换为基于 `$0` 的动态路径表达式，使包可重定位）
   - 对 mafft.tmpl 的 shebang 执行 sed 改写（`#!/bin/bash` → `#!/data/service/hnp/bin/bash`）
   - `make -C core CC=clang PREFIX=<package_folder> -j1`
   - make 从 mafft.tmpl 生成 mafft 脚本（因 patch 已移除 _LIBDIR，make 的 sed 无匹配，
     生成的脚本保留动态路径 `$(cd "$(dirname "$0")/.." && pwd)/libexec/mafft`）
   - make 编译约 30 个内部二进制（dvtditr, dndfast7, ..., version）
3. `package()`：
   - 内部二进制 → libexec/mafft/
   - mafft 脚本 + Ruby/Perl 辅助脚本 → bin/ 和 libexec/mafft/
   - 创建算法别名符号链接（linsi, ginsi, einsi, fftns, fftnsi, nwns, nwnsi 等）

## 关键适配点

### 1. shebang 改写（OHOS 无 /bin/bash）
mafft 主脚本由 mafft.tmpl 经 sed 生成，原始 shebang 为 `#! /bin/bash`。OHOS 无
`/bin/bash`，在 `build()` 中对 mafft.tmpl 执行 sed 改写为 `#!/data/service/hnp/bin/bash`，
之后 make 的 sed 生成最终 mafft 脚本时即携带正确 shebang。

### 2. PREFIX 与运行时路径（包可重定位）
mafft 脚本原本通过 `prefix=_LIBDIR`（被 make 的 sed 替换为 `PREFIX/libexec/mafft` 绝对
路径）查找内部二进制，导致包不可重定位。通过 `0001-mafft-relocatable-libdir.patch` 将
`_LIBDIR` 改为动态路径 `$(cd "$(dirname "$0")/.." && pwd)/libexec/mafft`，运行时根据
脚本自身位置（bin/mafft）推导出 libexec 目录（bin/../libexec/mafft），使包可部署到任意
路径。`MAFFT_BINARIES` 环境变量仍可覆盖此路径。PREFIX 仍传给 make，供 LIBDIR/BINDIR
安装路径和 mafft-profile/mafft-distance 符号链接使用。

### 3. 编译器覆盖（R33）
Makefile 默认 `CC = gcc`，通过命令行 `CC=clang` 覆盖。编译器从 Conan conf
`tools.build:compiler_executables:c` 获取，不使用 shell 环境变量。

### 4. 算法别名符号链接
linsi/ginsi/einsi/fftns/fftnsi/nwns/nwnsi 等为指向 mafft 脚本的符号链接（同一算法
不同策略入口）。without-extensions 版本不含 xinsi/qinsi（RNA 结构比对）。mafft-profile
和 mafft-distance 在 bin/ 下创建指向 libexec/ 的相对符号链接。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | mafft 脚本无法执行 | OHOS 无 /bin/bash | sed 改写 mafft.tmpl shebang 为 /data/service/hnp/bin/bash |
| 2 | mafft 找不到内部二进制 | 脚本硬编码 LIBDIR 路径不正确 | make 时传 PREFIX=package_folder |
| 3 | Makefile 用 gcc | 默认 CC=gcc | 命令行覆盖 CC=clang（R33） |
| 4 | 包不可重定位（P2） | mafft 脚本硬编码 PREFIX 绝对路径 | 0001-mafft-relocatable-libdir.patch 改为基于 $0 的动态路径 |

## 依赖
无第三方库依赖（libc + libm + libpthread）。Ruby/Perl 仅用于可选辅助脚本。

## 验证
- test_package：运行 `mafft --version` 校验版本号 7.525；对小 FASTA 文件执行比对，
  校验输出包含全部输入序列且为比对格式（含 gap 字符）。
