# signal-tlsd

## 简介

signal-tlsd 是 Signal 域前置 TLS 代理的独立 Rust 实现。它协商一个外部 TLS 握手并监听来自 Signal 客户端的入站 TLS 连接，内部 TLS 连接在客户端与 Signal 服务器之间保持端到端加密，外部 TLS 连接在代理处终止。这可用于规避基于 IP 封锁、DNS 过滤和基于 SNI 的深度包检测的审查。

## 功能概述

- **域前置 TLS 代理**：实现官方 Signal-TLS-Proxy 协议，单进程替代两个 nginx + docker-compose
- **允许列表**：默认内置 Signal 端点允许列表，可通过 `-A` 自定义
- **回退端点**：`-F` 选项将非 TLS / 不匹配 SNI 的连接转发到回退地址
- **SIGHUP 重载**：收到 SIGHUP 信号时从磁盘重载 TLS 证书，无需重启
- **外部 TLS 终止模式**：`-N` 跳过外部 TLS 层，适用于已由 nginx 等终止外部 TLS 的场景

## OHOS 适配

### 适配要点

- **构建系统**：Cargo（Rust edition 2024），无 configure 步骤，直接 `cargo build --release --bin signal-tlsd`
- **编译命令**：`cargo build --release --bin signal-tlsd`
- **上游测试**：`cargo test --release`（src/alpn.rs 7 个 + src/rules.rs 8 个，共 15 个单元测试）
- **安装方式**：复制编译后的二进制 `target/release/signal-tlsd` 到 `$PREFIX/bin`
- **静态链接**：Rust 程序通常静态链接标准库，依赖较少
- **ELF 签名**：需要对生成的二进制文件进行 ELF 签名（鸿蒙要求）

### 已知问题

- 无已知问题

## 依赖关系

- **Rust 工具链**：cargo / rustc（harmonybrew 1.95.0，target aarch64-unknown-linux-ohos）
- **Rust crate 依赖**（由 Cargo.lock 管理，非 Conan 包）：anyhow, arc-swap, bstr, clap, env_logger, indexmap, log, tokio, tokio-rustls
