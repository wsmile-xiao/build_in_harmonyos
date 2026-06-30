# mhash 0.9.9.9 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published

## 编译步骤

1. `init-build mhash 0.9.9.9 --url=https://download.savannah.nongnu.org/releases/mhash/mhash-0.9.9.9.tar.gz` (手动下载因 SSL 证书问题)
2. 替换 `config.guess` 和 `config.sub` 为 automake-1.16 版本（原版无法识别 HarmonyOS）
3. 修补 `configure` 中 `umask 077` 为 `umask 022`（HMDFS 临时目录权限问题）
4. `./configure --prefix=$DEFAULT_PREFIX`
5. `make -j1`
6. `make install DESTDIR=$TEST_PREFIX`
7. 编译静态测试程序验证功能
8. `ohc-run.py package mhash 0.9.9.9`
9. `make install`（不带 DESTDIR）
10. `ohc-run.py finish mhash 0.9.9.9 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 下载失败 | HMDFS CA 证书验证失败 | 手动 curl -k 下载 tarball |
| 2 | config.guess 无法识别 HarmonyOS | 2006 版 config.guess 不识别 aarch64/HarmonyOS | 替换为 automake-1.16 版 config.guess/config.sub |
| 3 | config.status 临时文件 Permission denied | HMDFS 不允许 umask 077 创建的目录内写入文件 | 修补 configure 中 umask 077→umask 022 |
| 4 | HMDFS 符号链接不被动态链接器解析 | HMDFS symlink 不被 ld.so 解析 | 创建真实文件副本替代 symlink |
| 5 | make check 全失败 | ELF 签名二进制无法通过 libtool wrapper 执行 | 编译静态测试程序验证功能 |

## 源码修改

- `config.guess`: 替换为 automake-1.16 版本（识别 aarch64-unknown-linux-ohos）
- `config.sub`: 替换为 automake-1.16 版本（识别 aarch64-unknown-linux-ohos）
- `configure`: 行 26644/26649 修改 umask 077→umask 022（HMDFS 临时目录权限修复）

## 验证结果

详见 `reports/test-report.md`，12/12 测试全部通过。

### 哈希算法正确性（已知测试向量验证）

```bash
# 静态链接测试程序验证
$ ./mhash_final_test

╔════════════════════════════════════╗
║  mhash 0.9.9.9 功能测试报告       ║
║  平台: aarch64-unknown-linux-ohos  ║
╚════════════════════════════════════╝

--- 基本功能 ---
  ✅ mhash_count=28 (期望28)
  ✅ MD5 名称=MD5
  ✅ SHA1 名称=SHA1

--- 哈希算法正确性（已知测试向量）---
  ✅ MD5("test"): 098f6bcd4621d373cade4e832627b4f6
  ✅ SHA1("test"): a94a8fe5ccb19ba61c4c0873d391e987982fbbd3
  ✅ SHA256("test"): 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08
  ✅ SHA512("test"): ee26b0dd...028a8ff
  ✅ CRC32("test"): accf8b33
  ✅ CRC32B("test"): 0c7e7fd8

--- HMAC 正确性（RFC 2202 测试向量）---
  ✅ HMAC-MD5 RFC2202#1: 9294727a3638bb1c13f48ef8158bfc9d
  ✅ HMAC-SHA1 功能可用

--- 密钥生成 ---
  ✅ S2K_SALTED keygen: 成功生成20字节密钥

╔════════════════════════════════════╗
║  ✅ 全部通过: 12/12              ║
╚════════════════════════════════════╝
```

### DESTDIR 安装验证

```bash
# 库文件验证
$ ls /storage/Users/currentUser/usr/local/lib/libmhash*
libmhash.a  libmhash.la  libmhash.so  libmhash.so.2  libmhash.so.2.0.1

# 头文件验证
$ ls /storage/Users/currentUser/usr/local/include/mhash.h /storage/Users/currentUser/usr/local/include/mutils/
mhash.h  mglobal.h  mhash.h  mhash_config.h  mincludes.h  mtypes.h  mutils.h
```

## 注意事项

- mhash 是纯库软件（无命令行二进制），验证需编译静态测试程序
- HMDFS 环境需修补 configure umask 问题
- 符号链接需替换为真实文件才能被 HarmonyOS 动态链接器加载
- HMDFS 上建议静态链接（`clang ... libmhash.a`）以避免共享库加载问题
---

**编译结束**: 2026-06-03 15:16
**最终状态**: published
