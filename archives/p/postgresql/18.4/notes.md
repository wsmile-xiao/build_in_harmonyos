# postgresql 18.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-09
- 编译器: clang/clang++ (clang 15.0.4)
- 状态: built

## 编译步骤

1. init-build: `python3 ohc-run.py init-build postgresql 18.4`
2. 手动补丁: config.guess, config.sub, configure
3. configure: `./configure --prefix=$DEFAULT_PREFIX --enable-thread-safety --without-icu`
4. make: `make -j2`
5. install: `make install DESTDIR=$TEST_PREFIX && make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | PG 18.x config.sub部分ohos支持已存在 | 上游已添加ohos*和linux-ohos* | 仅补充ohos* libc后缀和ohos-linux maybe_os |
| 2 | configure WARNING: unrecognized option --enable-thread-safety | PG 18.x已默认启用线程安全 | 不影响编译，可忽略 |
| 3 | HMDFS umask 077 导致临时目录创建失败 | HarmonyOS NEXT文件系统umask限制 | 修改configure umask 077→007, tmpdir改为${TMPDIR:-$HOME/tmp}/ |

## 源码修改

### config/config.guess
- 添加 `*:HarmonyOS:*:*` 检测模式（GUESS格式），支持aarch64/arm/x86_64/i686机器类型映射到linux-ohos

### config/config.sub
- 添加 `ohos-linux` 到 maybe_os 部分（识别ohos-linux组合）
- 添加 `ohos*` 到 libc suffix validation（`llvm* | musl* | newlib* | ohos* | relibc* | uclibc*`）
- 注意：PG 18.4 上游已包含 `ohos*` 在 basic system types (line 2070) 和 `linux-ohos*-` 在 kernel-os validation (line 2213)

### configure
- 修改 tmpdir: `"./confXXXXXX"` → `"${TMPDIR:-$HOME/tmp}/confXXXXXX"`
- 修改 umask: `077` → `007`

## PG 18.x 差异说明

PG 18.x 与 17.x/16.x 的主要差异:
- config.sub 已包含部分 ohos 支持（ohos* 基本类型和 linux-ohos* 内核验证）
- postgres 二进制文件为 ELF shared object（新构建结构）
- 需要较少的 config.sub 补丁（仅 ohos* libc后缀和 ohos-linux maybe_os）

## 依赖版本

- readline (system)
- openssl (已编译)
- zlib (系统)
- zstd (已编译)

## 验证结果

```bash
$ pg_config --version
PostgreSQL 18.4
$ postgres --version
postgres (PostgreSQL) 18.4
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| postgres-18.4-aarch64.tar.gz | TBD | aarch64 架构二进制包 |
| postgres-18.4-aarch64-debug.tar.gz | TBD | debug 符号包 |

## 源码修改清单

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|----------|
| config/config.guess | OHOS平台不识别 | 添加*:HarmonyOS:*:*检测行 | ✅ 0001-config-config.guess.patch |
| config/config.sub | OHOS libc后缀和maybe_os | 添加ohos* libc和ohos-linux | ✅ 0002-config-config.sub.patch |
| configure | HMDFS umask/tmpdir兼容 | 修改tmpdir和umask | ✅ 0003-configure.patch |

**编译日期**: 2026-06-09
**编译命令**: ./configure --prefix=$DEFAULT_PREFIX --enable-thread-safety --without-icu && make -j2 && make install DESTDIR=$TEST_PREFIX && make install
**关键适配**: HMDFS文件系统umask限制、OHOS平台检测、PG 18.x上游部分ohos支持
---

**编译结束**: 2026-06-09 19:45
**最终状态**: built