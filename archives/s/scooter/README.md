# scooter

交互式终端查找替换工具（Interactive find and replace in the terminal），使用 Rust 编写。

## 功能概述

- 交互式 TUI 查找与替换界面
- 支持正则表达式（含高级正则/look-ahead）、多行匹配、大小写匹配
- 支持固定字符串匹配、文件 glob 过滤、隐藏文件/Git 目录控制
- `--no-tui` 无界面快速查找替换、stdin 管道处理
- headless 模式可用于脚本化批量替换

## OHOS 适配

- Rust/cargo 工具链：worker 无 cargo/rustc 时通过 Harmonybrew bottles 引导
- crate 下载走 rsproxy.cn 镜像（sparse index），clang 作链接器（aarch64-unknown-linux-ohos）
- 删除上游 `rust-toolchain.toml`（channel 1.91 固定），使用可直接执行的工具链
- 上游 `cargo test --workspace` 956 个单元/集成测试全过（worker 无 rustdoc，4 个 doctest 跳过）

## 依赖关系

- 编译依赖：Rust/cargo（Harmonybrew fallback）；无 Conan C/C++ 依赖
- 唯一的原生 C 依赖为 `onig_sys`（由 two-face/syntect 默认特性引入），自动随 cargo 构建

## 参考资料

- 官网：https://github.com/thomasschafer/scooter
- 上游版本：v0.9.1