# wasmtime 45.0.0 适配笔记

## 编译环境
- 构建系统: cargo (Rust 项目)
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- Rust 版本: 1.95.0
- 状态: built

## 编译步骤

wasmtime 是一个 Rust 项目，使用 Cargo 作为构建系统，而非传统的 autotools/CMake。

1. 下载源码（使用 GitHub 加速镜像 ghfast.top）
2. 解压完整源码到 builds/wasmtime-45.0.0
3. 配置 Cargo 镜像源（使用清华 TUNA sparse+https://mirrors.tuna.tsinghua.edu.cn/crates.io-index/）
4. 设置 SSL_CERT_FILE 环境变量解决证书问题
5. 执行 `cargo build --release`
6. 安装二进制到 staging 和本地目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|---------|
| 1 | GitHub SSL 证书验证失败 | 系统 SSL 证书配置问题 | 使用 ghfast.top 加速镜像 + Python 禁用 SSL 验证下载 |
| 2 | Cargo 依赖下载 SSL 错误 | 同上 | 配置清华 TUNA 镜像 + 设置 SSL_CERT_FILE 环境变量 |
| 3 | curl 命令动态库加载失败 | 预编译 curl 不完整 | 使用 Python urllib 直接下载 |

## 源码修改

无源码修改，直接编译。

## 依赖版本

- rust: 1.95.0
- cargo: 1.95.0
- cmake: 4.1.2
- clang: 15.0.4

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/wasmtime --version
wasmtime 45.0.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| wasmtime | 69MB | CLI 二进制 |

## 注意事项

1. Rust 项目编译时间较长（约 31 分钟）
2. 需要配置国内 Cargo 镜像源加速依赖下载
3. wasmtime 是 WebAssembly 运行时，支持 WASI 和组件模型
4. 无 configure/make，直接使用 cargo build
---

**编译结束**: 2026-05-28 19:57
**最终状态**: built
