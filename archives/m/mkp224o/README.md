# mkp224o

## 简介

mkp224o 是 Tor v3 隐身服务（hidden service）的 vanity onion address 生成器：
反复生成 Ed25519 密钥对并检查公钥派生的 base32 地址前缀，找到带指定前缀的
`.onion` 地址。纯 C（C99），多线程（pthread），随机源来自 libsodium 的
randombytes。

## 功能概述

- `mkp224o [-t threads] [-n count] [-d dir] <prefix...>` — 搜索带指定
  前缀的 v3 onion 地址并输出密钥目录
- `-p` — passphrase 模式（libsodium ARGON2ID13 派生种子）
- 每个命中生成一个目录：`hostname`、`hs_ed25519_public_key`（64 字节）、
  `hs_ed25519_secret_key`（96 字节，Tor v3 格式）

## OHOS 适配

- 官方 release tarball（自带 configure，Autoconf 2.72 生成）直接构建，
  无补丁；仅 E129 HMDFS umask 处理（与 macchanger 同款）。
- Ed25519 后端保持上游默认 ed25519-donna（可移植 C）；x86-64 汇编后端
  均为 opt-in，aarch64 不涉及；无运行期 CPU 特性探测。
- libsodium 仅提供随机源与 passphrase KDF，密钥数学未替换实现。
- 产物 `bin/mkp224o` 经 binary-sign-tool 自签（.codesign 段）。
- 上游 `make test` 4 个 KAT 测试（base16/base32/base64/ed25519 RFC 8032
  向量）在 build() 内逐一执行；test_package 另含功能测试与 OHOS 特有
  检查（ELF64 AArch64、musl 解释器、.codesign、无 RPATH、多线程真实
  生成、密钥清理）。

## 依赖关系

- libsodium/1.0.22（随机源 randombytes_buf、sodium_init、passphrase 模式
  crypto_pwhash）

## 参考资料

- 官方源码: https://github.com/cathugger/mkp224o
- License: CC0-1.0
