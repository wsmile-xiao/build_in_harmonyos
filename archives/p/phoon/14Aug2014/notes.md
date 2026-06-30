# phoon 14Aug2014 适配笔记

## 编译环境
- 构建系统: makefile (plain Makefile, no configure script)
- 编译日期: 2026-06-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 源码下载: curl -kL https://www.acme.com/software/phoon/phoon_14Aug2014.tar.gz (Python urllib SSL失败，用curl下载)
2. init-build: ohc-run.py init-build phoon 14Aug2014 --no-download
3. 修改 Makefile: 添加 DESTDIR/PREFIX 支持, 修改 CC=clang, 去掉 -s(LDFLAGS), 调整 CFLAGS
4. make: 成功编译，仅有 warnings (unused vars, UTF-8 in comment)
5. make install DESTDIR=$TEST_PREFIX: staging 验证
6. make install: 本地安装到 $DEFAULT_PREFIX
7. 验证: /storage/Users/currentUser/usr/local/bin/phoon 运行成功，显示月相

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Python urllib SSL下载失败 | SSL证书握手失败 | 用curl -kL下载tarball，然后init-build --no-download |
| 2 | 源码无configure脚本 | phoon使用纯Makefile | 直接修改Makefile添加PREFIX/DESTDIR支持 |

## 源码修改

- 修改 Makefile: 添加 PREFIX=$DEFAULT_PREFIX, DESTDIR 支持, CC=clang, CFLAGS调整, 去掉LDFLAGS=-s

## 依赖版本

- 无依赖（仅需要 -lm 数学库）

## 验证结果

```bash
$ phoon
# 显示当前月相图 (New Moon + 0 12:16:29)
# 验证成功
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| phoon-14Aug2014-ohos-aarch64.tar.gz | ~6KB | 预编译包 |

## 注意事项

- phoon 无 autotools configure 脚本，使用纯 Makefile
- 原始 Makefile 不支持 DESTDIR，需要手动添加
- BSD-2-Clause 许可证
---

**编译结束**: 2026-06-15 23:27
**最终状态**: built
