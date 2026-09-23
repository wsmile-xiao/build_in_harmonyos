# rust-toolchain — OpenHarmony 编译档案

## 软件简介

Rust 编译器工具链包（rustc + cargo + `aarch64-unknown-linux-ohos` 目标标准库），
经 rustup 从 rsproxy.cn 镜像引导安装，打包为 Conan 包。

**用途**：竞赛 CI 无系统级 Rust 工具链（SKILL CI 能力矩阵：Rust ❌ → env_unsupported，
除非先立项 rust 工具链包）。本包作为 `tool_requires` 供 Rust 配方（如 below）引用，
使 `conan create` 能在 CI 干净环境构建 Rust 包。

## 适配要点（路径 B：贡献创新）

- 非现成三方库适配，而是**新建的平台基础设施包**（PR 模板"适配路径"填"路径 B（贡献创新）"）
- 构建期引导：`rustup-init.sh`（rsproxy.cn）→ `rustup toolchain install 1.97.1 --profile minimal`
  → `rustup target add aarch64-unknown-linux-ohos`
- cargo registry 替换为 rsproxy 镜像（`config.toml`）
- 包内自包含 `cargo/`（CARGO_HOME）与 `rustup/`（RUSTUP_HOME），
  `package_info` 通过 `bindirs=["cargo/bin"]` + `buildenv CARGO_HOME/RUSTUP_HOME`
  自动注入下游构建环境

## 验证

- `conan create`：test_package 校验 rustc/cargo 版本、OHOS target 已安装、
  交叉编译 hello 并在本机（HarmonyOS aarch64）运行
- 下游实证：below 0.11.0（Rust 包）以本工具链完成编译+链接+测试 399/414=96.4%

## 已知限制

- 工具链包体积较大（数百 MB），构建依赖 CI 环境可访问 rsproxy.cn
- 工具链为宿主架构相关（aarch64 OHOS 宿主）
- 二进制上传制品仓需 CI Release 机器凭据
