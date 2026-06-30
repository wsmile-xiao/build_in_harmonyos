# aespipe 2.4j 适配笔记

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-06-10
- 编译器: clang 15.0.4 / clang++
- 平台: OpenHarmony aarch64 (HMDFS 文件系统)
- 状态: published

## 编译步骤

1. 初始化：`ohc-run.py init-build aespipe 2.4j --url=...`
   - 源码下载因 SSL 证书问题需手动 `curl -kL` 下载后放到 `~/tmp/builds/` 目录
2. 修改 configure 脚本（见下方源码修改）
3. 运行 `./configure --prefix=$DEFAULT_PREFIX` — ✅ PASS
4. 运行 `make -j1` — ✅ PASS（编译 aespipe.o, aes.o, md5.o, sha512.o, rmd160.o → aespipe）
5. 运行 `make install DESTDIR=$TEST_PREFIX` — ✅ PASS（staging 安装）
6. 运行 `make check` — ⚠️ 跳过（aespipe 不提供 test 目标）
7. Staging 验证 + 预编译包制作 — ✅ PASS
8. 本地安装 `make install`（不带 DESTDIR）— ✅ PASS
9. 用户验证 `~/usr/local/bin/aespipe --help` — ✅ PASS，版本 2.4j
10. 收尾 `ohc-run.py finish aespipe 2.4j published` — ✅ 完成

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 失败：config.status 无法创建 `./confXXXXXX/subs1.awk`，报 Permission denied | HMDFS ACL 强制目录组权限 `rws`（setgid），umask 077 剥夺组权限后 ACL 阻止 owner 写入子目录中的文件 | 修改 configure 中 mktemp 创建临时目录的代码，去掉 `umask 077`，生成补丁 0001-configure.patch |
| 2 | clean-verify G0 失败：`/bin/sh: no closing quote` | (a) clean_verify.py 用 `/bin/sh`（toybox sh）运行 configure，toybox sh 不支持 autotools configure 中的 bash 特性；(b) configure_options YAML 列表解析正则生成含未闭合引号的命令字符串 | (a) 修改 clean_verify.py 使用 `bash ./configure`；(b) 改进 YAML 列表格式解析逻辑 |
| 3 | 源码 SSL 下载失败 | 系统缺少 CA 证书，urlopen 报 CERTIFICATE_VERIFY_FAILED | 手动 `curl -kL` 下载后放到脚本期望的路径，init-build 检测到已有 tarball 自动跳过下载 |

## 源码修改

**0001-configure.patch**: 修改 configure 脚本第 7260-7270 行临时目录创建逻辑

修改内容：
- 去掉 `(umask 077 && mktemp -d "./confXXXXXX")` 中的 `umask 077`
- 去掉 `(umask 077 && mkdir "$tmp")` 中的 `umask 077`
- 原因：HMDFS ACL 强制目录组权限为 `rws`，umask 077 剥夺组权限后导致 owner 也无法写入子目录中创建的文件

关键验证数据：
```
umask 077 && mktemp -d → drwx--S--- → owner 无法写入 ✗
mktemp -d（无 umask） → drwxrws--x → owner 可写入 ✓
```

## 依赖版本

无依赖（aespipe 是独立工具，仅使用 libc）

## 验证结果

```bash
$ ~/usr/local/bin/aespipe --help 2>&1 | head -2
version 2.4j  Copyright (c) 2002-2025 Jari Ruusu, (c) 2001 Dr Brian Gladman

# 管道模式 AES-256 加密解密往返测试
$ echo "pipe test data" | aespipe -e aes256 -H sha512 -P pass.txt | aespipe -e aes256 -H sha512 -d -P pass.txt
pipe test data  ← 原文完整还原

# 100KB 大文件加密解密往返
$ cmp large.bin large-dec.bin → 退出码 0（二进制完全一致）

# 错误密码解密
$ cmp large.bin wrong-dec.bin → 退出码 1（数据不同，密码校验有效）

$ file ~/usr/local/bin/aespipe
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| aespipe-2.4j-ohos-aarch64.tar.gz | 96KB | 预编译包（ELF 签名，strip 后） |
| aespipe-2.4j-ohos-aarch64-debug.tar.gz | 31KB | 调试符号包 |
| 0001-configure.patch | 1KB | HMDFS ACL 修复补丁 |

## 注意事项

1. HMDFS 上 umask 077 会破坏 ACL 组权限（rws），导致 owner 无法在创建的子目录中写入文件。所有使用 autotools 的软件都可能遇到此问题。
2. aespipe 不提供 `make check` 测试套，需手动功能验证
3. aespipe configure 检测到 `output architecture: unknown`，不会使用任何优化的汇编 AES 代码（armv4/armv8ce/armv8sca/x86/amd64），仅使用纯 C 实现
4. aespipe 默认密码最少 20 字符（aes256 模式下），测试时需使用足够长的密码
5. toybox sh (`/bin/sh`) 不支持 autotools configure 中的 bash 特性，clean-verify 需使用 bash 运行

---

**编译结束**: 2026-06-10
**最终状态**: published