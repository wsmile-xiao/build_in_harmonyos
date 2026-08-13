# argc

## 简介

argc 是一个 bash CLI 框架与 bash 命令运行器。在 shell 脚本顶部用注释（`@cmd`/`@option`/`@flag`/`@arg`/`@env`/`@meta` 等）声明参数规范，`argc` 即可自动生成参数解析代码、帮助文本、shell 补全（bash/zsh/fish/tcsh/nushell/elvish/xonsh/powershell），并支持 Argcfile.sh 任务自动化。

## 功能概述

- **注解式参数声明**: 用注释声明 option/flag/arg/env，自动生成解析与校验
- **自动补全**: 生成 bash/zsh/fish/tcsh/nushell/elvish/xonsh/powershell 补全脚本
- **Man 页生成**: 自动生成 man page
- **环境变量集成**: `@env` 声明、校验并绑定环境变量
- **任务自动化**: 通过 Argcfile.sh 实现 bash 命令运行器
- **跨平台**: macOS / Linux / Windows / BSD

## OHOS 适配

### 适配要点

- **构建系统**: Cargo（Rust），无需 configure 步骤
- **编译命令**: `cargo build --release --bin argc`
- **工具链**: OHOS 预检沙盒可能无 cargo/rustc，经 Harmonybrew 安装 Rust（dua-cli 先例）
- **链接器**: 设置 `CC=CXX=clang`、`RUSTFLAGS="-C linker=clang"`（OHOS 无 cc 符号链接）
- **TMPDIR**: OHOS /tmp 只读，构建与测试使用可写 TMPDIR
- **静态链接**: Rust 二进制默认静态链接，无 RPATH 需求
- **上游测试**: `cargo test --release`（13 src 单元测试 + 183 #[test] + 25 #[rstest] 集成测试）

### 已知问题

- 无已知问题（纯 Rust 实现，无平台相关 C/C++ 代码）

## 依赖关系

### 编译依赖

- rust（cargo + rustc，Harmonybrew 提供）

### 运行依赖

- 无特殊依赖（静态链接）；运行时需要 bash（OHOS 提供 /data/service/hnp/bin/bash）

## 参考资料

- 官网: https://github.com/sigoden/argc
- 源码: https://github.com/sigoden/argc
- 文档: https://github.com/sigoden/argc/tree/main/docs
