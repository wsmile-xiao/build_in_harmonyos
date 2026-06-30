# pgpdump 0.37 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. init-build 下载并解压源码
2. 应用补丁 `0001-configure.patch`（sed umask 077→022，E011 HMDFS 平台适配）
3. `CONFIG_SHELL=/data/service/hnp/bin/bash ./configure --prefix=$DEFAULT_PREFIX` 成功（config.status 正常运行）
4. `make -j2` 编译成功
5. `make install DESTDIR=$TEST_PREFIX` staging 安装成功
6. `make install` 本地安装成功
7. `ohc-run.py package` 预编译包制作成功 (157KB)
8. `ohc-run.py finish` 归档收尾完成

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Python SSL 下载失败 | SSL 证书验证失败 | 用 wget 手动下载 tarball |
| 2 | config.status Permission denied | E011: HMDFS setgid 继承父目录 owner(20001006)，mktemp 创建临时目录 umask 077，当前用户(20020089)无法写入 | sed configure 中 umask 077→022（E011推荐方案），生成 0001-configure.patch |
| 3 | pgpdump -v 显示 "0.36" | 上游源码 pgpdump.c 硬编码版本字符串 "0.36"，tag 0.37 未更新 | 上游问题，不影响功能 |
| 4 | make check 无目标 | pgpdump 无测试套 | 使用源码自带 data/ 测试数据手动验证 |

## 补丁说明

- `0001-configure.patch`: 将 configure 脚本中 `umask 077` 改为 `umask 022`，解决 HMDFS 上 mktemp 创建临时目录后当前用户无法写入的问题（E011 平台适配）

## 功能验证

使用源码自带 `data/` 目录测试数据验证：

```bash
$ pgpdump -v
pgpdump version 0.36, Copyright (C) 1998-2024 Kazu Yamamoto

$ diff <(pgpdump -u data/pub) data/pub.res  # PASS
$ diff <(pgpdump data/enc) data/enc.res     # PASS
$ diff <(pgpdump -u data/sig) data/sig.res  # PASS

# RSA 3072-bit key、ECC Curve25519 key 均正确解析
# 所有选项 (-a/-g/-i/-l/-m/-u) 正常工作
```

## 依赖版本

- zlib: 系统预编译包 (-lz)

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pgpdump-0.37-ohos-aarch64.tar.gz | 157KB | 预编译包 |
| pgpdump-0.37-ohos-aarch64-debug.tar.gz | debug符号包 | 预编译包 |
| 0001-configure.patch | umask 077→022 | HMDFS E011 平台适配补丁 |
---

**编译结束**: 2026-05-25 15:59
**最终状态**: built
