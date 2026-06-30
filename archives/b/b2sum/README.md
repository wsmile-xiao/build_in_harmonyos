# b2sum

BLAKE2 b2sum 参考实现命令行工具 — 用于计算 BLAKE2b/BLAKE2s/BLAKE2bp/BLAKE2sp 哈希校验值。

## 简介

b2sum 是 BLAKE2 参考实现中的命令行工具，功能类似于 md5sum/sha256sum，但计算的是 BLAKE2 系列哈希。BLAKE2 是一种快速、安全的哈希算法，比 SHA-2 更快，比 MD5 更安全。

支持 4 种算法变体：
- **BLAKE2b**: 512位输出（默认），适用于 64位平台
- **BLAKE2s**: 256位输出，适用于 32位平台
- **BLAKE2bp**: BLAKE2b 并行版本
- **BLAKE2sp**: BLAKE2s 并行版本

## OpenHarmony 编译说明

- aarch64 平台必须使用 `ref/` 纯 C 实现（不可使用 `sse/` SSE 优化）
- 必须使用 GNU ld 替代 lld（ELF 签名兼容性）
- 需禁用 OpenMP（musl 环境缺少运行时）
- `build_subdir: b2sum`（源码嵌套在 BLAKE2 仓库的 b2sum/ 子目录内）

## 许可证

CC0-1.0 OR OpenSSL OR Apache-2.0

## 主页

https://blake2.net

## 版本历史

| 版本 | 日期 | 状态 | 备注 |
|------|------|------|------|
| 20190724 | 2026-06-09 | published | aarch64 构建，使用 ref 纯 C 实现 |