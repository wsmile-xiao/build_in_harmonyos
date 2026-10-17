# libhydrogen — HarmonyOS/OpenHarmony 预编译包

## 软件简介

libhydrogen 是 jedisct1（Frank Denis）开发的轻量级、安全、易用的密码学库。
它实现与 WireGuard 协议相同的密码学原语（Gimli 置换、X25519 密钥交换、
Ed25519 风格签名、secretbox 认证加密、KDF、pwhash 等），面向资源受限环境，
单一翻译单元、零外部依赖，只需 C99 编译器。

**主要功能**：
- 认证加密：secretbox（Gimli）
- 签名：hydro_sign（Ed25519 风格，Gimli 为底）
- 密钥交换：X25519（kx_n/kk/xx/nk 模式）
- 密钥派生：KDF、pwhash
- 哈希：Gimli 哈希
- 随机数：/dev/urandom（POSIX，musl 兼容）

**上游**：https://github.com/jedisct1/libhydrogen （ISC License）

## 适配版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.0-git.264bf42 | built | master @ 264bf42 快照，CMake 零补丁适配 |
