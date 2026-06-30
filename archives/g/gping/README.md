# gping - Ping with a graph

## 软件描述
gping 是一个跨平台的命令行工具，用于 ping 目标并以图表形式显示延迟数据。它是传统 ping 命令的图形化替代品，使用 Rust 编写。

## 功能特性
- 实时图形显示 ping 延迟
- 支持多个目标同时 ping
- 支持 DNS 查询图表
- 跨平台支持（Linux、Windows、macOS）

## 构建信息
- **构建系统**: Cargo (Rust)
- **语言**: Rust
- **依赖**: Rust 工具链 (rustc + cargo)

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.20.1-r0 | ❌ failed | 2026-05-25 | 缺少 Rust 工具链 |

## 外部链接
- GitHub: https://github.com/orf/gping
- crates.io: https://crates.io/crates/gping

## 注意事项
- gping 是 Rust 项目，需要 Rust 工具链才能编译
- 在 musl 系统（如鸿蒙）上需要 musl 版本的 Rust 工具链
- 编译前需确保网络可访问 crates.io 或配置离线依赖