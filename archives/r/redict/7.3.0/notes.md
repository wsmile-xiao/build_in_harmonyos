# redict 7.3.0 适配笔记

## 编译环境
- 构建系统: makefile（基于 Redis 构建系统，无 configure 脚本）
- 编译日期: 2026-06-13
- 编译器: clang/clang++ (aarch64-unknown-linux-ohos, clang 15.0.4)
- 状态: published

## 编译步骤

```bash
# 解压源码到 .work 目录
cd /storage/Users/currentUser/tmp/builds/redict-7.3.0.work

# 编译（MALLOC=libc 替代默认的 jemalloc）
make -j2 CC=clang CXX=clang++ MALLOC=libc CFLAGS="-fPIC -O2" LDFLAGS="-lm"

# 安装到 staging 目录
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-redict-7.3.0 PREFIX=/storage/Users/currentUser/usr/local

# 本地安装
make install PREFIX=/storage/Users/currentUser/usr/local

# 验证
/storage/Users/currentUser/usr/local/bin/redict-server --version
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | redict 默认在 Linux 上使用 jemalloc | jemalloc 在 HarmonyOS/musl 上兼容性差 | 使用 `MALLOC=libc` 参数替代 jemalloc |

说明：redict 7.3.0 在 HarmonyOS aarch64 上编译时无需修改任何源码，仅需在 make 命令中指定 `MALLOC=libc` 即可完成编译。任务描述中提到的 setproctitle、fstatfs、secure_getenv 等潜在问题在本版本中均未出现。

## 源码修改

无源码修改。编译过程干净通过，不需要任何补丁。

## 依赖版本

- clang 15.0.4 (target: aarch64-unknown-linux-ohos)
- musl libc (HarmonyOS)

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/redict-server --version
Redis server v=7.2.4 sha=00000000:0 malloc=libc bits=64 build=8b6a716fd4f52c89

$ ls /storage/Users/currentUser/tmp/test-install-redict-7.3.0/storage/Users/currentUser/usr/local/bin/
redict-benchmark  redict-check-aof  redict-check-rdb  redict-cli  redict-sentinel  redict-server

$ file /storage/Users/currentUser/usr/local/bin/redict-server
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| redict-7.3.0-ohos-aarch64.tar.gz | - | 主交付包（6个二进制 + 配置文件） |
| redict-7.3.0-ohos-aarch64-debug.tar.gz | - | 调试符号包 |

## 注意事项

- redict 是 Redis OSS 7.2.4 的 LGPL-3.0 分支，`--version` 输出仍显示 "Redis server v=7.2.4"
- 二进制名称从 redis-* 改为 redict-*（redict-server, redict-cli, redict-benchmark, redict-check-rdb, redict-check-aof, redict-sentinel）
- 编译时必须使用 `MALLOC=libc`，不能用默认的 jemalloc
- 未使用 TLS 支持（如需 TLS，需额外指定 BUILD_TLS=yes 及 openssl 依赖）
---

**编译结束**: 2026-06-13 12:25
**最终状态**: built
