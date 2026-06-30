# postgresql 17.10 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-09
- 编译器: clang/clang++ (clang 15.0.4)
- 状态: built

## 编译步骤

1. init-build: `python3 ohc-run.py init-build postgresql 17.10`
2. 手动补丁: config.guess, config.sub, configure
3. configure: `./configure --prefix=$DEFAULT_PREFIX --enable-thread-safety --without-icu`
4. make: `make -j2`
5. install: `make install DESTDIR=$TEST_PREFIX && make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure WARNING: unrecognized option --enable-thread-safety | PG 17.x已默认启用线程安全 | 不影响编译，可忽略 |
| 2 | HMDFS umask 077 导致临时目录创建失败 | HarmonyOS NEXT文件系统umask限制 | 修改configure umask 077→007, tmpdir改为${TMPDIR:-$HOME/tmp}/ |

## 源码修改

### config/config.guess
- 添加 `*:HarmonyOS:*:*` 检测模式（GUESS格式），支持aarch64/arm/x86_64/i686机器类型映射到linux-ohos

### config/config.sub
- 添加 `ohos-linux` 到 maybe_os 部分（识别ohos-linux组合）
- 添加 `ohos*` 到 libc suffix validation（`llvm* | musl* | newlib* | ohos* | relibc* | uclibc*`）
- 添加 `ohos*` 到 basic system types（`gnu* | android* | ohos* | bsd* | ...`）
- 添加 `linux-ohos*-` 到 kernel-os validation

### configure
- 修改 tmpdir: `"./confXXXXXX"` → `"${TMPDIR:-$HOME/tmp}/confXXXXXX"`
- 修改 umask: `077` → `007`

## 依赖版本

- readline (system)
- openssl (已编译)
- zlib (系统)
- zstd (已编译)

## 验证结果

```bash
$ pg_config --version
PostgreSQL 17.10
$ postgres --version
postgres (PostgreSQL) 17.10
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| postgres-17.10-aarch64.tar.gz | TBD | aarch64 架构二进制包 |
| postgres-17.10-aarch64-debug.tar.gz | TBD | debug 符号包 |

## 源码修改清单

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|----------|
| config/config.guess | OHOS平台不识别 | 添加*:HarmonyOS:*:*检测行 | ✅ 0001-config-config.guess.patch |
| config/config.sub | OHOS平台不识别 | 添加ohos-linux、ohos*、linux-ohos* | ✅ 0002-config-config.sub.patch |
| configure | HMDFS umask/tmpdir兼容 | 修改tmpdir和umask | ✅ 0003-configure.patch |

**编译日期**: 2026-06-09
**编译命令**: ./configure --prefix=$DEFAULT_PREFIX --enable-thread-safety --without-icu && make -j2 && make install DESTDIR=$TEST_PREFIX && make install
**关键适配**: HMDFS文件系统umask限制、OHOS平台检测
---

**编译结束**: 2026-06-09 19:26
**最终状态**: built