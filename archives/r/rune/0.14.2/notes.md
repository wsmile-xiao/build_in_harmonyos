# rune 0.14.2 适配笔记

## 编译环境

- 构建系统：Cargo workspace
- 编译日期：2026-08-19
- 编译器：Rust 1.95.0、clang 15.0.4
- 目标平台：HarmonyOS arm64（aarch64-unknown-linux-ohos）
- 状态：built

## 编译步骤

```bash
cargo build --release -p rune-cli
cargo test --release -p rune --lib
```

Conan 配方使用官方 0.14.2 标签源码，通过 rsproxy sparse registry 获取 Rust crates，并显式配置 clang 为 OHOS Rust 链接器。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 通用构建驱动无法识别构建系统 | 驱动未识别 Cargo.toml | 使用 Cargo custom 配方构建 rune-cli |
| 2 | OHOS 默认缺少 cc 链接器 | rustc 默认链接器不可用 | 在 Cargo target 配置中指定 clang |
| 3 | /tmp 不可写 | OHOS 构建环境限制 | 使用用户目录下的可写 TMPDIR |

## 源码修改

未修改上游源码，无补丁。

## 依赖版本

无 Conan 依赖；Rust crates 由 Cargo 根据上游 workspace 元数据解析。

## 验证结果

```text
cargo build --release -p rune-cli: PASS
cargo test --release -p rune --lib: 293 passed, 0 failed, 1 ignored
rune script smoke test: PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/rune | Rune 语言解释器 |

## 注意事项

上游 CLI 的 `--version` 输出不包含语义版本号，仅输出解释器名称，因此消费者测试同时验证帮助信息与实际 Rune 脚本执行。
---

**编译结束**: 2026-08-19 15:12
**最终状态**: built
