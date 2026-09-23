# scrypt 1.3.2 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-16
- 编译器: clang 15 (LLVM)
- 状态: built（本机 W3 通过，CI 上传待 PR 合入）

## 编译步骤

```bash
tar -xzf scrypt-1.3.2.tgz && cd scrypt-1.3.2
# 1) config.aux/config.guess + config.sub 需打 OHOS 补丁（E007），否则
#    configure 报 "cannot guess build type"（uname -s = HarmonyOS）
# 2) configure 硬性要求 OpenSSL（AC_SEARCH_LIBS AES_encrypt + openssl/aes.h），
#    通过 ConanAutotoolsDeps 注入依赖 include/lib
export CC=clang CFLAGS="-fPIC -O2"
./configure --prefix=/usr/local CPPFLAGS="-I<openssl>/include" \
    LDFLAGS="-L<openssl>/lib -Wl,-rpath,<openssl>/lib" LIBS="-lcrypto"
make -j1 && make install
```

## 适配要点
- E007：config.guess 增加 `*:HarmonyOS:*:*` 分支输出
  `aarch64-unknown-linux-ohos`（2018 版脚本还缺 echo/exit，补丁一并修复）；
  config.sub 增加 ohos-linux 分支、ohos* OS 列表、linux-ohos 内核列表。
- openssl/3.5.8.1 为构建与运行依赖（AES_encrypt、HMAC、openssl/aes.h）。
- 产物为 CLI 工具 bin/scrypt（R38：软件级 commands.json 已声明）。

## 测试
- 上游：make test = 9/10 通过（05-system-scrypt 需系统 scrypt，本平台无，
  上游设计为 SKIP）；verify-strings 4 组向量与 .good 完全一致。
- 鸿蒙专项：tests/ohos_roundtrip_test.sh（版本 + 加解密往返 + 错误口令必败）。
- test_package 消费者：直接执行 bin/scrypt 版本/往返/错误口令 → PASSED。

## 已知问题与解决
1. GitHub 直连超时（gh 镜像均不可达）→ 使用官方发布站点
   https://www.tarsnap.com/scrypt/scrypt-1.3.2.tgz（GPG 签名 SHA-256
   d632c119... 已核对一致）。
2. registry openssl/3.5.8.1 的 x86-64 残留二进制不可用 → 用 OHOS profile
   匹配的静态包（opens8df.../lib/libcrypto.a）。
---

**编译结束**: 2026-09-17 10:30
**最终状态**: built
