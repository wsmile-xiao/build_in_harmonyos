# Rune

Rune 是一种可嵌入 Rust 应用的动态编程语言。本项目适配 Rune **0.14.2** 的命令行解释器到 OpenHarmony PC / aarch64。

## 功能概述

- 解析、检查并执行 Rune 脚本
- 提供格式化、测试、基准测试和文档命令
- 提供语言服务器与 ACE 自动补全支持
- 可作为 Rust 库嵌入应用，也可通过 `rune` 命令独立使用

## OHOS 适配

- 使用 HarmonyOS 原生 Rust 工具链构建 Cargo workspace 中的 `rune-cli` 包
- 为 `aarch64-unknown-linux-ohos` 显式配置 clang 链接器
- 使用可写的用户目录作为 `TMPDIR`
- 使用 rsproxy sparse registry，避免 crates.io CDN 在 CI 环境中超时
- 未修改上游源码，无补丁

## 验证

- `cargo build --release -p rune-cli`：通过
- `cargo test --release -p rune --lib`：293 通过、0 失败、1 忽略
- Conan 消费者测试：版本、帮助、语法检查、脚本执行和无效源码拒绝均通过

## 参考资料

- 项目主页：https://rune-rs.github.io
- 上游仓库：https://github.com/rune-rs/rune
- 版本归档：`archives/r/rune/0.14.2/`
