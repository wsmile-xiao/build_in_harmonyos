# ldid 2.1.5-procursus7 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-17
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 源码来源: GitHub ProcursusTeam/ldid (git clone --depth 1)
2. 依赖编译: 先编译 libplist-2.6.0 (autotools, --without-cython)
3. ldid 使用简单 Makefile 构建:
   ```bash
   export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
   make PREFIX=$DEFAULT_PREFIX
   make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | libplist缺失 | ldid硬依赖libplist-2.0（#include <plist/plist.h>），pkg-config找不到 | 先编译安装libplist-2.6.0到~/usr/local |
| 2 | libplist configure失败 | git clone无RELEASE_VERSION和.git，m4_esyscmd无法获取版本 | 创建.tarball-version文件，设置RELEASE_VERSION=2.6.0环境变量后autoreconf |
| 3 | libplist Python/Cython绑定配置失败 | harmonybrew python不完整 | configure加--without-cython |
| 4 | init-build自动URL搜索失败 | ldid不在标准下载源中 | 使用--url=file:///local/path手动指定本地tarball |

## 源码修改

无补丁。ldid源码无需修改即可在鸿蒙上编译。

## 依赖版本

- libplist: 2.6.0 (手动编译)
- openssl/libcrypto: 3.5.6 (预编译包)
- libcnary: 内嵌于libplist源码

## 验证结果

```bash
$ ldid --version
Link Identity Editor 2.1.5-procursus7
$ ldid -h
(显示帮助信息，确认功能可用)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ldid-2.1.5-procursus7-ohos-aarch64.tar.gz | (待打包) | 预编译包 |
| ldid | 264768 | 二进制可执行文件 |
| ldid.1 | manpage | 帮助文档 |

## 注意事项

- ldid是Mach-O伪代码签名工具，在鸿蒙上主要用于Mach-O格式处理
- 鸿蒙ELF签名使用ohc-run.py sign-elf，ldid作为补充工具
- ldid --version 不是标准格式，输出包含usage信息
- libplist是必须的硬依赖，无法禁用plist功能
---

**编译结束**: 2026-06-17 07:50
**最终状态**: built
