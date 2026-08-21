# b43-fwcutter 019 — 适配笔记

## 概述

b43-fwcutter 是一个从 Broadcom 43xx 无线驱动的二进制文件中提取固件的工具。
提取的固件供开源 b43/b43legacy Linux 无线驱动使用。

## 上游信息

- 主页: https://bues.ch/b43/fwcutter/
- 源码: https://bues.ch/b43/fwcutter/b43-fwcutter-019.tar.bz2
- Git: https://github.com/b43-fwcutter/b43-fwcutter
- 许可证: BSD 2-clause

## 构建系统分析

- 纯 Makefile 项目，无 configure 脚本
- 源文件: fwcutter.c + md5.c → b43-fwcutter 二进制
- 使用 C99 标准（-std=c99 -Wall -pedantic）
- 依赖: 仅标准 C 库（byteswap.h, stdlib.h, stdio.h, string.h 等）
- 无外部库依赖
- 上游无测试套件（无 make check 目标）

## 真机验证结果 (2026-08-21)

- 环境: HarmonyOS aarch64, HongMeng Kernel 1.12.0
- Profile: ohos-local (clang-15, sysroot, code-sign)
- Conan: 2.31.1
- conan create 结果: ✅ 全部通过
  - 源码下载: ✅ bues.ch tar.bz2
  - 解压: ✅ Conan Python tarfile（Toybox tar 不支持 bzip2 但 Conan 绕过）
  - 编译: ✅ clang-15，仅有 linker flag unused 警告
  - 打包: ✅ b43-fwcutter binary + man page
  - test_package: ✅ 5/5 全部 PASS
    - Binary exists: PASS
    - Usage output: PASS
    - Version 019: PASS
    - -l list mode: PASS (19 drivers)
    - Missing file error: PASS

## OHOS 适配要点

1. **无外部依赖**: W0 依赖检查通过
2. **byteswap.h**: bionic libc 支持，无兼容性问题
3. **-D_BSD_SOURCE**: OHOS bionic 兼容
4. **Makefile install**: 使用 `install -o 0 -g 0`，手动 cp 替代
5. **ELF 签名**: ohos-local profile 的 LDFLAGS 含 `-Wl,--code-sign`，链接时自动处理
6. **Toybox tar**: 不支持 bzip2，但 Conan get() 用 Python 处理不受影响

## 下一步

- issue: 待补（未在项目内找到明确 issue 编号）
- 提 PR 前需 rebase origin/main
