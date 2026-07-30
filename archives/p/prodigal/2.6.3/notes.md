# prodigal 2.6.3 适配笔记

## 编译环境
- 构建系统: makefile（纯Makefile，无configure脚本）
- 编译日期: 2026-06-09
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码：`https://github.com/hyattpd/Prodigal/archive/refs/tags/v2.6.3.tar.gz`
2. 编译：`make CC=clang LDFLAGS="-fuse-ld=/data/service/hnp/bin/ld.bfd" -j2`
3. Staging安装：`cp prodigal $TEST_PREFIX/$DEFAULT_PREFIX/bin/`（Makefile不支持DESTDIR）
4. 预编译包制作：`ohc-run.py package prodigal 2.6.3`
5. 本地安装：`make install INSTALLDIR=$DEFAULT_PREFIX/bin`
6. 验证：`prodigal -v`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile不支持DESTDIR | 原始Makefile硬编码INSTALLDIR，无DESTDIR机制 | 手动cp到$TEST_PREFIX/$DEFAULT_PREFIX/bin/，并额外复制到$TEST_PREFIX/bin/供verify脚本检查 |
| 2 | 需使用GNU ld替代lld | OHOS平台lld可能不兼容 | LDFLAGS="-fuse-ld=/data/service/hnp/bin/ld.bfd" |
| 3 | prodigal --version不支持 | 软件只支持-v而非--version | 使用-v进行版本验证 |

## 源码修改

无源码修改，编译通过无需补丁。

## 依赖版本

- clang 15.0.4
- GNU ld (binutils) 2.45
- 无外部库依赖（仅需 -lm）

## 验证结果

```bash
$ prodigal -v
Prodigal V2.6.3: February, 2016

$ file /storage/Users/currentUser/usr/local/bin/prodigal
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| prodigal-2.6.3-ohos-aarch64.tar.gz | 27417KB | 预编译包 |

## 注意事项

- 纯Makefile项目，通过make变量传递编译参数，无configure脚本
- 必须使用GNU ld（-fuse-ld=/data/service/hnp/bin/ld.bfd）
- Makefile INSTALLDIR需显式覆盖为$DEFAULT_PREFIX/bin
- 版本验证用-v而非--version
- 无make check测试目标
---

**编译结束**: 2026-07-16 00:18
**最终状态**: built
