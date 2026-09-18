# Etebase C Library

> Etebase 端到端加密后端的 C 客户端库（Rust 实现 + C API）

## 简介

libetebase 是 Etebase（Encrypt Everything）的 C 客户端库。上游用 Rust 实现核心
加密与协议逻辑，通过 cbindgen 暴露 C API，打包产物为 `libetebase.so`、
`etebase.h` 与 `etebase.pc`，下游可直接以 C ABI 集成端到端加密的
collection/item 同步能力。

## OHOS 适配要点

- Rust 工具链由 `rust-toolchain/1.97.1` 基础设施包提供（`tool_requires`），
  不使用 rustup 引导；工具链二进制需自签名后 OHOS loader 才会执行。
- crates 走 rsproxy.cn 镜像拉取；系统 C 依赖（libsodium、OpenSSL）来自制品仓。
- 上游 `c_tests` 共 12 个用例，其中 3 个离线可运行（真机实测），9 个需要
  live Etebase server（`ETEBASE_TEST_API_URL`），如实申报为跳过。
- 上游仅提供 cdylib 共享库目标，配方默认 `shared=True`。
- 链接名是 `etebase`（`-letebase`），头文件位于 `include/etebase/`。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| libsodium | 1.0.22 | sodiumoxide-sys 的系统 libsodium |
| openssl | 3.5.6 | openssl-sys 的系统 OpenSSL |
| rust-toolchain | 1.97.1 | 构建期工具链（tool_requires） |

## 功能验证

```bash
pkg-config --modversion etebase  # 期望输出: 0.5.8
```

## 参考

- [官方文档](https://docs.etebase.com)
- [源码仓库](https://github.com/etesync/libetebase)
