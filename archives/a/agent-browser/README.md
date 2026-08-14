# agent-browser

## 简介

agent-browser 是一个面向 AI 代理的浏览器自动化 CLI（Rust 原生实现，vercel-labs 出品）。
通过 Chrome DevTools Protocol（CDP）驱动浏览器，为 AI 代理提供页面导航、元素交互、
截图、网络监控、无障碍审计（axe-core）、MCP 工具集成等能力。

## 功能概述

- **浏览器自动化**: 通过 CDP 驱动 Chrome，支持导航/点击/输入/滚动等交互
- **AI 代理友好**: CLI + MCP 工具，输出结构化 JSON，便于代理消费
- **无障碍审计**: `agent-browser a11y [url]`，axe-core 引擎 + WCAG 标签过滤
- **截图与快照**: 页面截图、无障碍快照、DOM 快照
- **网络与存储**: 网络请求监控、cookies/storage 查看
- **doctor 诊断**: `agent-browser doctor --offline` 离线自检（CLI/Chrome/环境）

## OHOS 适配

### 适配要点

- **构建系统**: Cargo（Rust），Cargo manifest 位于仓库 `cli/` 子目录，无 configure 步骤
- **编译命令**: `cargo build --release --manifest-path cli/Cargo.toml`
- **工具链**: OHOS 预检沙盒可能无 cargo/rustc，经 Harmonybrew bottle 引导安装（argc/1.24.0 先例）
- **链接器**: 设置 `CC=CXX=clang`、`RUSTFLAGS="-C linker=clang"`（OHOS 无 cc 符号链接）
- **crates 镜像**: rsproxy.cn sparse 镜像（设备无 crates.io CA bundle）
- **TMPDIR**: OHOS /tmp 只读，构建与测试使用可写 TMPDIR
- **静态链接**: Rust 二进制默认静态链接，无 RPATH 需求
- **上游测试**: `cargo test --release --tests --manifest-path cli/Cargo.toml`
  （886 个 #[test] 单元测试 + doctor_cli.rs 集成测试；需要 Chrome 的 e2e/parity
  用例上游已 #[ignore]；doc-tests 阶段因 OHOS 工具链无 rustdoc 排除，平台限制先例）

## 安装与使用

```bash
# Conan 安装（在鸿蒙 PC 应用工程中）
conan install --requires=agent-browser/0.33.0

# 命令行使用
agent-browser --version
agent-browser --help
agent-browser doctor --offline --quick --json
```

## 上游信息

- 仓库: https://github.com/vercel-labs/agent-browser
- 主页: https://agent-browser.dev
- 许可证: Apache-2.0
