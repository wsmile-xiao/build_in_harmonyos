# trippy 0.13.0 适配笔记

## 编译环境
- 构建系统: cargo (Rust)
- 编译日期: 2026-06-18
- 编译器: rustc 1.95.0 / clang (for C deps)
- 状态: published

## 编译步骤

1. 下载源码: `https://github.com/fujiapple852/trippy/archive/refs/tags/0.13.0.tar.gz`
2. 修复 `include_str!` 路径问题:
   - `cp trippy-config-sample.toml crates/trippy-tui/trippy-config-sample.toml`
   - `cp README.md crates/trippy/README.md`
3. 构建: `CARGO_HOME=/data/storage/el2/base/cache/cargo-home cargo build --release`
4. 安装到 staging: `cp target/release/trip $TEST_PREFIX/$DEFAULT_PREFIX/bin/`
5. 本地安装: `cp target/release/trip $DEFAULT_PREFIX/bin/`
6. 打包: `ohc-run.py package trippy 0.13.0`

## 遇到的问题与解决方案

| # | 问题 | 因 | 解决方案 |
|---|------|------|----------|
| 1 | `include_str!("../trippy-config-sample.toml")` 失败 | GitHub archive 解压后，workspace 成员的相对路径与原始 git 结构不同 | 复制 `trippy-config-sample.toml` 到 `crates/trippy-tui/` |
| 2 | `#![doc = include_str!("../README.md")]` 失败 | 同上，workspace 根目录的 README.md 不在 `crates/trippy/` | 复制 `README.md` 到 `crates/trippy/` |

## 依赖版本

- Rust toolchain: rustc 1.95.0, cargo 1.95.0
- musl libc (dynamic linking)

## 验证结果

```bash
$ trip --version
trip 0.13.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| trippy-0.13.0-ohos-aarch64.tar.gz | 9786KB | 预编译包（含 ELF 签名、strip、RPATH） |
| trip (binary) | ~9.97MB → strip后更小 | 主二进制 |

## 注意事项

- 测试套件 (`cargo test`) 需要 CAP_NET_RAW/root 权限，在构建环境中跳过
- 动态链接 musl libc，需确保目标系统有 `/lib/ld-musl-aarch64.so.1`
---

**编译结束**: 2026-06-18 02:02
**最终状态**: published
