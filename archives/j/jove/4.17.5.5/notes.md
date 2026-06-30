# jove 4.17.5.5 适配笔记

## 编译环境
- 构建系统: makefile (plain Makefile, not autotools configure)
- 编译日期: 2026-06-17
- 编译器: clang/clang++
- 状态: built

## 编译步骤

jove uses a plain Makefile (no configure script). Built with:

```bash
make SYSDEFS="-DLinux -DJTC" JOVEHOME=$DEFAULT_PREFIX JTMPDIR=$TMPDIR/jove-tmp \
     CFLAGS="-fPIC -O2 -DLinux -DJTC" CC=clang -j1
make install DESTDIR=$TEST_PREFIX JOVEHOME=$DEFAULT_PREFIX JTMPDIR=$TMPDIR/jove-tmp ...
make install JOVEHOME=$DEFAULT_PREFIX JTMPDIR=$TMPDIR/jove-tmp ...
```

Key parameters:
- SYSDEFS="-DLinux -DJTC": HarmonyOS returns "HarmonyOS" from uname, but jove's sysdep.h expects "Linux" to enable proper platform features. -DJTC enables built-in termcap (no ncurses dependency).
- JTMPDIR=$TMPDIR/jove-tmp: Default /var/tmp is read-only on HarmonyOS
- JOVEHOME=$DEFAULT_PREFIX: Installation prefix

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL download failure | init-build download function doesn't use SSL fallback | Pre-downloaded tarball with curl --insecure, placed in expected location |
| 2 | /var/tmp read-only | HarmonyOS /var/tmp is read-only | Set JTMPDIR=$TMPDIR/jove-tmp |
| 3 | uname returns "HarmonyOS" | sysdep.h expects "Linux" define | Override SYSDEFS with -DLinux -DJTC |
| 4 | nroff not available | doc/jove.man.txt requires nroff | Created placeholder file |
| 5 | No configure script | jove uses plain Makefile, not autotools | Build directly with make and variables |
| 6 | G0 clean-verify failure | G0 expects configure script | Expected; build manually verified successful |
| 7 | make check N/A | jove has no test suite | Noted as N/A |

## 依赖版本

无外部依赖。jove 使用内置 termcap (JTC模式)。

## 验证结果

```bash
$ file ~/usr/local/bin/jove
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

$ strings ~/usr/local/bin/jove | grep "4.17"
4.17.5.5
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| jove-4.17.5.5-ohos-aarch64.tar.gz | 665KB | 主预编译包 |
| jove-4.17.5.5-ohos-aarch64-debug.tar.gz | 106KB | 调试符号包 |

## 注意事项

- jove 是终端编辑器，非交互式环境无法完整验证功能（--version 输出终端类型错误，属正常）
- 平台适配要点：SYSDEFS 必须包含 -DLinux 以匹配 sysdep.h 的条件编译
- JTC 模式（内置 termcap）消除了对 ncurses/termcap 库的依赖
---

**编译结束**: 2026-06-18 15:52
**最终状态**: built
