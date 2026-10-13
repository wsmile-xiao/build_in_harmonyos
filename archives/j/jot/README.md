# jot

轻量终端笔记管理工具（`jt` 二进制），适配 HarmonyOS PC (aarch64)。

- 上游：[shashwatah/jot](https://github.com/shashwatah/jot)（Homebrew `jot` 稳定版 0.1.2）
- 语言：Rust（cargo 项目）
- 构建产物：`jt`
- 许可证：MIT
- 版本：0.1.2

## 适配说明

本项目为 Rust/cargo 项目，原生构建需要 Rust 工具链（cargo/rustc，
`aarch64-unknown-linux-ohos`）。构建命令 `cargo build --release`，产物 `jt` 安装到 `bin/`。
作为命令行工具，已在软件级目录声明 `commands.json`（R38）。
