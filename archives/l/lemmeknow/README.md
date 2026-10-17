# lemmeknow

## 简介

lemmeknow 是一个网络安全/取证领域的字符串识别工具（Rust 编写）：输入一段文本或一个文件，基于内置的 140 条正则规则识别其中的 IP 地址、URL、电子邮箱、API 密钥、云服务令牌、加密货币地址、哈希等模式，支持最小/最大稀有度过滤、tag 包含/排除、boundaryless 模式与 JSON 输出。

## 功能概述

- **文本识别**: 对字符串识别 140 种已知模式（IP、URL、邮箱、密钥、令牌等）
- **文件扫描**: 直接扫描文件内容逐行识别
- **稀有度过滤**: `--min` / `--max` 控制误报与置信度
- **tag 过滤**: `--include` / `--exclude` 按标签筛选结果
- **JSON 输出**: `-j` 机器可读输出，便于管道集成
- **跨平台**: Linux / macOS / Windows / WASM

## OHOS 适配

### 适配要点

- **构建系统**: Cargo（Rust，edition 2021），`cargo build --release --locked`
- **工具链**: 设备无 cargo/rustc，经 Conan `tool_requires` 引用制品仓 `rust-toolchain/1.97.1`（宿主与目标均为 aarch64-unknown-linux-ohos）
- **签名**: rust-lang dist 工具链与最终产物需 `binary-sign-tool -selfSign 1` 自签名（OHOS 拒绝执行未签名 ELF）
- **运行库**: cargo 自身动态链接 OpenSSL/zlib，用 harmonybrew bottle 并显式 `LD_LIBRARY_PATH`
- **crates 拉取**: rsproxy.cn sparse 镜像 + 设备 CA bundle（`SSL_CERT_FILE`）
- **TMPDIR**: OHOS /tmp 只读，构建与测试使用 `~/tmp` 等可写目录
- **依赖**: 无 C/C++ 依赖（Cargo.lock 123 项全为纯 Rust），产物静态链接 Rust std

### 已知问题

- 无已知问题（纯 Rust 实现，无平台相关 C/C++ 代码；上游 10 个测试真机全通过）

## 依赖关系

### 编译依赖

- rust-toolchain/1.97.1（Conan tool_requires，rust-lang 官方 dist 预编译 OHOS 工具链）

### 运行依赖

- 无特殊依赖（纯 Rust 静态产物）

## 参考资料

- 官网: https://github.com/swanandx/lemmeknow
- 源码: https://static.crates.io/crates/lemmeknow/lemmeknow-0.8.0.crate
- crates.io: https://crates.io/crates/lemmeknow
