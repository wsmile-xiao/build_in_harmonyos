# jaq 3.1.0 适配笔记

## 编译环境
- 构建系统: cargo (Rust workspace)
- 编译日期: 2026-06-18
- 编译器: rustc (aarch64-linux-ohos)
- 状态: built

## 编译步骤

1. `cargo build --release` 编译整个 workspace
2. 产物: `target/release/jaq`
3. 手动安装到 staging: `cp target/release/jaq $TEST_PREFIX/$DEFAULT_PREFIX/bin/`
4. 安装到 DEFAULT_PREFIX: `cp target/release/jaq $DEFAULT_PREFIX/bin/`

> 注意：jaq 是 Rust/Cargo 项目，init-build 误识别为 autotools。实际应使用 cargo 编译。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 构建系统误识别 | init-build 将 Cargo 项目识别为 autotools | 手动用 cargo build --release 编译 |
| 2 | 未生成 staging 目录 | cargo 无 make install DESTDIR 概念 | 手动 cp 二进制到 staging |
| 3 | verify-build 无二进制 | staging 目录结构与 verify 期望不匹配 | 在 $TEST_PREFIX/bin/ 也放置二进制 |

## 源码修改

- `0001-jaq-Cargo.toml.patch`: Cargo.toml 平台适配
- `0002-jaq-src-funs.rs.patch`: funs.rs 平台适配

## 依赖版本

无外部依赖（Rust 静态编译）

## 验证结果

```bash
$ jaq --version
jaq 3.1.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| jaq-3.1.0-ohos-aarch64.tar.gz | 3533KB | 预编译包 |

## 注意事项

- jaq 是 Rust 项目，不支持 DESTDIR 模式，需手动安装二进制
- verify-build 需要在 $TEST_PREFIX/bin/ 放置二进制（非 $TEST_PREFIX/$DEFAULT_PREFIX/bin/）
---

**编译结束**: 2026-06-21 16:00
**最终状态**: built
