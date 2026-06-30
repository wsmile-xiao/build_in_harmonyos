# paperkey 1.6 适配笔记

## 编译环境
- 构建系统: autotools (Autoconf 2.66)
- 编译日期: 2026-06-17
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published
- 平台: aarch64-unknown-linux-gnu-ohos (HarmonyOS, HMDFS)

## 编译步骤

1. 下载源码: `https://github.com/dmshaw/paperkey/releases/download/v1.6/paperkey-1.6.tar.gz`
2. 应用补丁: `sed -i 's/umask 077/umask 022/g' configure`（E011 HMDFS umask 权限修复）
3. 配置: `./configure --prefix=/storage/Users/currentUser/usr/local`
4. 编译: `make -j1`
5. 测试: `make check` — All 6 tests passed
6. 安装(staging): `make install DESTDIR=/storage/Users/currentUser/tmp/test-install-paperkey-1.6`
7. 打包: `ohc-run.py package paperkey 1.6`
8. 安装(本地): `make install`（不带 DESTDIR，模拟用户部署）
9. 用户验证: `paperkey --version` → `paperkey 1.6 (linux-gnu-ohos)`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.status: can't create ./confXXX/subs1.awk: Permission denied` | HMDFS UID 映射导致 umask 077 创建的临时目录不可写 (E011) | `sed -i 's/umask 077/umask 022/g' configure`，生成补丁 0001-configure-remove-umask-077.patch |
| 2 | init-build 无法自动搜索到下载 URL | 搜索引擎返回无关结果 | 手动从 jabberwocky.com 发现 URL |
| 3 | refresh-patch 自动生成含生成文件的补丁(config.h/config.log/config.status/papertest-*) | edit-tracker 追踪了所有变更文件包括生成文件 | 手动精选，仅保留 configure umask 源码补丁 |
| 4 | G0 clean-verify 失败 | toybox `patch` 不支持 `--input` 选项 | 平台限制，非代码问题；手动验证通过 |

**关键发现**: paperkey 1.6 使用 Autoconf 2.66，configure 正确检测 `aarch64-unknown-linux-gnu-ohos`，无需修改 config.guess/config.sub。

## 源码修改

仅修改 `configure` 文件2处:
- 行 9793: `umask 077` → `umask 022`（mktemp 临时目录创建）
- 行 9798: `umask 077` → `umask 022`（mkdir 临时目录创建）

对应补丁: `0001-configure-remove-umask-077.patch`

## 依赖版本

无外部库依赖（纯 C 项目，仅使用 gnulib 内嵌模块：getopt、sha1、unistd 等）

## 验证结果

```bash
$ make check
rsa dsaelg ecc eddsa PASS: roundtrip.sh
rsa dsaelg ecc eddsa PASS: roundtrip-raw.sh
PASS: bad-crc-base16.sh
PASS: bad-crc-raw.sh
PASS: bad-primary.sh
PASS: bad-subkey.sh
==================
All 6 tests passed

$ paperkey --version
paperkey 1.6 (linux-gnu-ohos)
Copyright (C) 2007, 2008, 2009, 2012, 2013, 2016, 2017, 2018 David Shaw <dshaw@jabberwocky.com>

$ file /storage/Users/currentUser/usr/local/bin/paperkey
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| paperkey-1.6-ohos-aarch64.tar.gz | 90K | 预编译包（已 ELF 签名、已 strip） |
| paperkey-1.6-ohos-aarch64-debug.tar.gz | 31K | 调试符号包 |
| 0001-configure-remove-umask-077.patch | 945B | configure umask 修复补丁 |

## 注意事项

- 此软件为纯 C 命令行工具（OpenPGP 密钥纸质备份），无外部库依赖
- umask 补丁是 HMDFS 平台通用问题（E011），对所有 autotools 项目生效
- configure 使用 Autoconf 2.66，平台 triplet 检测无需额外修改

---
**编译结束**: 2026-06-17
**最终状态**: published
---

**编译结束**: 2026-06-17 18:09
**最终状态**: published
