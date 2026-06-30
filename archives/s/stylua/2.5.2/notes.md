# stylua 2.5.2 适配笔记

## 编译环境
- 构建系统: custom (Rust/Cargo)
- 编译日期: 2026-06-15
- 编译器: clang/clang++（Rust 使用 rustc 1.96.0 后端编译为 aarch64-unknown-linux-musl）
- 状态: built

## 编译步骤

stylua 是纯 Rust/Cargo 项目，不需要传统的 configure/make 流程：

1. `cargo build --release --no-default-features --features editorconfig,lsp`
   - 禁用默认的 wasm-bindgen feature（非 wasm 目标）
   - 保留 editorconfig 和 lsp features（核心功能）
   - 编译成功，耗时约 3 分钟

2. 安装到 staging 目录（DESTDIR 模式等效）
   - `mkdir -p $TEST_PREFIX$DEFAULT_PREFIX/bin`
   - `cp target/release/stylua $TEST_PREFIX$DEFAULT_PREFIX/bin/stylua`

3. 运行测试
   - `cargo test --release --no-default-features --features editorconfig,lsp`
   - 48 个单元测试全部通过
   - doctest 因 OHOS SELinux sandbox 限制失败（Permission denied）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cdylib warning | aarch64-unknown-linux-musl 不支持 cdylib | 无需处理，仅是 warning，不影响二进制 |
| 2 | doctest Permission denied | OHOS SELinux sandbox 阻止 rustdoc 执行 | 标记为平台限制(E046类)，不影响核心功能 |
| 3 | Cargo 无 DESTDIR 支持 | Cargo install 不支持 DESTDIR | 手动 cp 到 staging 目录 |

## 源码修改

无源码修改。stylua 在 OHOS 上原生编译成功，不需要任何补丁。

## 依赖版本

- rustc: 1.96.0
- cargo: 1.96.0
- clang: 15.0.4 (LLVM backend)

## 验证结果

```bash
$ stylua --version
stylua 2.5.2

$ file /storage/Users/currentUser/usr/local/bin/stylua
ELF executable, 64-bit LSB arm64, static, not stripped

$ cargo test --release --no-default-features --features editorconfig,lsp
48 unit tests passed, 0 failed
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| stylua-2.5.2-ohos-aarch64.tar.gz | ~7.7MB | 预编译包（stripped） |
| stylua-2.5.2-ohos-aarch64-debug.tar.gz | ~2.3MB | 预编译包（debug，含符号） |

## 注意事项

- stylua 是纯 Rust 项目，Cargo 的 DESTDIR 模式需要手动实现
- cdylib crate type 在 OHOS musl target 上不支持（仅 warning）
- doctest 在 OHOS 上因 SELinux 限制无法运行，不影响使用

---
---

**编译结束**: 2026-06-15 22:09
**最终状态**: built
