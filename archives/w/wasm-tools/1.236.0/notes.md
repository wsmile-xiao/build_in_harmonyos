# wasm-tools 1.236.0 适配笔记

## 编译环境
- 构建系统: cargo (Rust)
- 编译日期: 2026-06-17
- 编译器: rustc 1.95.0
- 状态: published

## 编译步骤

1. 源码下载: `https://github.com/bytecodealliance/wasm-tools/archive/refs/tags/v1.236.0.tar.gz`
2. 初始化: `ohc-run.py init-build wasm-tools 1.236.0 --url=...`
   - 注意: init-build 自动检测了嵌套源码 (crates/c-api)，将子目录提升为主目录，需要手动恢复完整 workspace 源码
   - 修复: 删除 .work 和 .orig 目录，重新解压完整 tarball，手动设置 .work 和 .orig 目录
3. 编译: `cargo build --release`
   - wasm-tools 是 Rust workspace 项目，包含多个 crate (wasmparser, wasm-encoder, wasmprinter 等)
   - 编译成功，仅有 warnings (unused variables)，无 errors
4. 安装: 手动复制 `target/release/wasm-tools` 到 staging 和 prefix 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 嵌套源码检测错误 | crates/c-api 子项目被误提升为主目录 | 手动删除 .work/.orig，重新解压完整 workspace 源码 |
| 2 | BUILD_SYSTEM 误识别为 autotools | Rust 项目被误识别 | 手动修改 manifest.yaml 的 build.system 为 cargo |

## 源码修改

无补丁，源码无需修改即可编译通过。

## 依赖版本

- rustc: 1.95.0
- cargo: 1.95.0

## 验证结果

```bash
wasm-tools --version → wasm-tools 1.236.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| wasm-tools-1.236.0-ohos-aarch64.tar.gz | 5.2MB | 预编译包 |

## 注意事项

- wasm-tools 是 Rust workspace 项目，init-build 的嵌套检测可能误判子目录结构
- 编译仅需 `cargo build --release`，无需 configure/make
- 产物仅为单个二进制 `wasm-tools`

**编译结束**
**最终状态**: published
---

**编译结束**: 2026-06-18 00:47
**最终状态**: published
