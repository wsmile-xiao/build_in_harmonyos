# E096: Rust 工具链不可用 — HarmonyOS 不在 Rust 官方支持平台

## 错误描述

编译 Rust 项目（如 gleam、ripgrep、fd、bat 等）时，发现 Rust/Cargo 工具链不可用。

**典型错误日志**:
```
zsh: command not found: rustc
zsh: command not found: cargo
error: unrecognized OS type: HarmonyOS
```

## 根因分析

HarmonyOS 不在 Rust 官方支持平台列表中。rustup 安装脚本会检测操作系统类型，遇到 HarmonyOS 时无法识别，直接报错退出。

**受影响的软件范围**:
- gleam (Erlang/Elixir 风格编程语言编译器)
- ripgrep (高性能搜索工具)
- fd (文件查找工具)
- bat (cat 替代品)
- starship (shell 提示符)
- 其他所有使用 Cargo.toml 构建的 Rust 项目

## 验证命令

```bash
which rustc && which cargo && rustc --version && cargo --version
```

如果上述命令都执行成功并输出版本信息，则 Rust 工具链已安装。

## 解决方案

### 方案 1: 安装预编译包 (推荐)

前提条件：需要先将 Rust 工具链加入 cmd-pkgs 预编译包仓库。

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- rust 1.81.0
```

### 方案 2: 手动下载 tarball (备选)

从 rust-lang.org 下载预编译的 aarch64-linux-gnu tarball：

```bash
curl -L -o rust.tar.gz https://static.rust-lang.org/dist/rust-1.81.0-aarch64-unknown-linux-gnu.tar.gz
tar xf rust.tar.gz
./rust-1.81.0-aarch64-unknown-linux-gnu/install.sh --prefix=$HOME/usr/local
```

**注意**: tarball 约 465MB，下载速度可能很慢（约 9KB/s），预计需要 14+ 小时。

### ⚠️ 禁止操作

- ❌ 不要使用 rustup：它会报错 "unrecognized OS type: HarmonyOS"
- ❌ 不要尝试 cargo build：没有工具链，命令无法执行

## 长期建议

1. **短期**: 将 Rust 工具链加入 cmd-pkgs 预编译包仓库
2. **长期**: 向 Rust 官方提交 HarmonyOS 平台支持 PR

## 相关条目

- E001: C 编译器不可用
- E012: ar 命令不可用

## 元数据

| 字段 | 值 |
|------|-----|
| severity | 3 (blocking) |
| category | toolchain, platform, rust |
| phase | configuration, compilation |
| contributor | 0D0A |
| created | 2026-05-09 |
| source | gleam 1.13.0-r0 编译失败 |