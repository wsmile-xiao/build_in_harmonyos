# taskwarrior-tui for HarmonyOS/OpenHarmony

> **编译日期**: 2026-06-05
> **状态**: ✅ built — 编译通过 + 预编译包就绪
> **构建系统**: Cargo (Rust)

## 软件简介

taskwarrior-tui 是 taskwarrior 的终端用户界面，提供交互式任务管理体验。

**为什么鸿蒙需要它？** 配合 taskwarrior 提供更直观的任务管理界面。

## OHOS 适配说明

- Rust/Cargo 项目，使用 `cargo build --release` 编译
- 无源码修改，使用官方源码直接编译
- 需 Rust 工具链（cargo 1.95.0+）

## 依赖关系

### 编译依赖
- Rust/Cargo >= 1.95.0

### 运行依赖
- taskwarrior（功能依赖，不影响编译）

## 参考资料

- **源码仓库**: https://github.com/kdheepak/taskwarrior-tui
- **crates.io**: https://crates.io/crates/taskwarrior-tui

## 版本历史

- **0.27.0** (2026-06-05): Built for OpenHarmony