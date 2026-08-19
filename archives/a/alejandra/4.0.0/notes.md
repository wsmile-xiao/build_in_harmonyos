# Alejandra 4.0.0 适配笔记

## 编译环境

- 构建系统：Cargo
- 编译日期：2026-08-19
- 编译器：系统 rustc 1.95.0，CI 缺失时引导 Harmonybrew rustc 1.97.1（均为 `aarch64-unknown-linux-ohos`）
- 状态：built

## 编译步骤

```bash
export TMPDIR="$HOME/tmp/alejandra"
export CARGO_TARGET_DIR="$PWD/target"
cargo build --release --locked --target=aarch64-unknown-linux-ohos
cargo test --release --locked --target=aarch64-unknown-linux-ohos -p alejandra --test fmt
cargo test --release --locked --target=aarch64-unknown-linux-ohos -p alejandra_cli --test cli
```

最终配方使用 Conan 隔离的可写 `TMPDIR` 和 `CARGO_TARGET_DIR`，并将目标目录中的 release 版 `alejandra` 安装到包的 `bin/` 目录。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 初始化脚本将构建系统误识别为 Autotools | 通用检测器未识别工作区根目录的 Cargo.toml | 配方明确使用 Cargo 构建系统 |
| 2 | 上游 CLI 快照套件初始失败 | OHOS 自动签名器向每个子进程的 stderr 注入签名诊断，改变精确快照 | 测试改用 Cargo 提供的已构建二进制，并仅过滤平台注入诊断；33/33 CLI case 保持原始快照断言并通过 |
| 3 | CI Worker 无 `cargo`/`rustc` | OHOS 预检沙盒默认不部署 Rust 工具链 | 优先探测系统工具链；缺失时下载 SHA256 固定的 Harmonybrew Rust、OpenSSL、zlib 和 CA bottle，并使用 `cargo.real` 构建 |
| 4 | CI 引导工具链报 `linker cc not found` | Worker 仅提供 `clang`，Rust build script 默认查找 `cc` | Cargo target 配置显式指定 Conan clang，并在构建目录创建 `cc`/`gcc` 兼容别名加入 PATH |
| 5 | Cargo 访问 rsproxy 报自签名证书链错误 | Worker 的 Cargo/libcurl 未自动使用可用 CA bundle | 优先探测 Worker CA；缺失时解包 SHA256 固定的 CA bottle，并通过 Cargo 配置与环境变量显式指定证书文件 |

## 源码修改

应用 `0001-cli-test-use-built-binary.patch` 测试可移植性补丁：CLI 测试直接运行 Cargo 提供的已构建二进制，并仅过滤 OHOS 注入的自动签名诊断。产品源码、33 组测试输入、预期快照和退出码断言均未修改。

## 依赖版本

使用上游 `Cargo.lock` 锁定的 crates.io 依赖；无额外 Conan 运行时依赖。

## 验证结果

```text
cargo build --release --locked: PASS
cargo test --release -p alejandra --test fmt: 43/43 cases passed
cargo test --release -p alejandra_cli --test cli: 33/33 cases passed
上游测试合计: 76/76 (100%)
消费者测试: --version、格式化、--check 共 3/3 通过
ELF: ELF64, AArch64, PIE
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/alejandra` | HarmonyOS PC arm64 命令行格式化工具 |
| `licenses/UNLICENSE` | 上游许可证 |

## 注意事项

上游 CLI 测试兼容补丁只排除 OHOS 运行时注入的自动签名诊断，不忽略 Alejandra 自身 stderr，也不更新或弱化上游快照。
---

**编译结束**: 2026-08-19 05:05
**最终状态**: built
