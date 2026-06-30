# usage 3.4.0 适配笔记

## 编译环境
- 构建系统: custom (Rust/Cargo)
- 编译日期: 2026-06-08
- 编译器: rustc 1.95.0 / cargo 1.95.0
- 状态: published

## 编译步骤

1. Source build context: `.build-context-usage-3.4.0`
2. cd `$BUILD_SRC_DIR` (= /data/storage/el2/base/cache/builds/usage-3.4.0.work)
3. `cargo build --release` — 编译成功 (1m 51s)
4. `cargo test --release` — 10 unit tests passed, doc-tests skipped (E051: Permission denied on exec syscall)
5. cp `target/release/usage` → `$TEST_PREFIX/$DEFAULT_PREFIX/bin/` (DESTDIR staging per R20)
6. cp `target/release/usage` → `$DEFAULT_PREFIX/bin/` (local install per R20 Step 6)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build URL search timeout for "usage" on GitHub | GitHub network timeout from mainland China | Used crates.io URL: `https://crates.io/api/v1/crates/usage-cli/3.4.0/download` |
| 2 | GitHub release binary download timeout | Same network issue | Built from source via cargo instead |
| 3 | doc-tests fail with "Permission denied (os error 13)" | E051: OpenHarmony unimplemented exec syscall in rustdoc | Skipped doc-tests; unit tests all pass |

## 源码修改

无源码修改，无补丁。Rust 项目直接从 crates.io 源码包构建。

## 依赖版本

- rustc 1.95.0 (59807616e 2026-04-14)
- cargo 1.95.0 (f2d3ce0bd 2026-03-21)
- clang 15.0.4 (系统工具链)

## 验证结果

```bash
$ $DEFAULT_PREFIX/bin/usage --version
usage-cli 3.4.0

$ $DEFAULT_PREFIX/bin/usage --help
CLI for working with usage-based CLIs
Commands: bash, complete-word, exec, fish, generate, lint, powershell, zsh

$ $TEST_PREFIX/$DEFAULT_PREFIX/bin/usage --version
usage-cli 3.4.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| usage | 10.5 MB | CLI for working with usage-based CLIs (Rust release build) |

## 注意事项

- "usage" is a Rust project (jdx/usage), not a C/autotools project — requires cargo to build
- GitHub direct access is unreliable from mainland China; crates.io is more reliable
- doc-tests fail on OpenHarmony due to E051 (Permission denied on exec in rustdoc)
- Build system detected as "autotools" by init-build (incorrect); manually corrected to "custom" in manifest
---

**编译结束**: 2026-06-08 15:11
**最终状态**: published
