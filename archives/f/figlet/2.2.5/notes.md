# figlet 2.2.5 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-15
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤

1. 下载源码: ftp://ftp.figlet.org/pub/figlet/program/unix/figlet-2.2.5.tar.gz
2. 解压源码
3. 应用补丁: patch -p1 < patches/0001-utf8.h.patch
4. 编译: `make CC=clang LD=clang CFLAGS="-fPIC -O2 -Wall" XCFLAGS="-DTLF_FONTS -DDEFAULTFONTDIR=\"...\" -DDEFAULTFONTFILE=\"standard\"" -j1 all`
5. 安装: `make install prefix=... BINDIR=... MANDIR=... DEFAULTFONTDIR=...`
6. 测试: `make check` (26/26 通过)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `__BEGIN_DECLS` 未定义 | utf8.h 缺少 `<sys/cdefs.h>` 头文件 | 添加 `#include <sys/cdefs.h>` |
| 2 | 链接失败 `gcc: No such file` | Makefile LD=gcc，OHOS 无 gcc | 覆盖 LD=clang |

## 源码修改

- utf8.h: 添加 `#include <sys/cdefs.h>` (patches/0001-utf8.h.patch)

## 依赖版本

无外部依赖。figlet 是独立的 C 程序。

## 验证结果

```bash
$ figlet -I 1
20205
$ figlet Hello
 _   _      _ _
| | | | ___| | | ___
| |_| |/ _ \ | |/ _ \
|  _  |  __/ | | (_) |
|_| |_|\___|_|_|\___/
$ make check
 All tests passed. (26/26)
```
---

**编译结束**: 2026-07-15 22:48
**最终状态**: published
