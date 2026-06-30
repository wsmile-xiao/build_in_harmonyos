# viu — 终端图片查看器

viu 是一个用 Rust 编写的终端图片查看器，支持在终端中显示 PNG、JPEG、GIF 等图片格式。

- 版本: v1.6.1
- 构建系统: Cargo (Rust)
- 编译器: rustc 1.95.0
- 许可证: MIT

## 编译说明

viu 可直接通过 `cargo build --release` 编译，无需源码修改。

### OHOS 编译注意

1. 需要修复 cargo 的 RUNPATH（patchelf + sign-elf）才能在 OHOS musl ldso 上运行
2. 并行编译时必须使用独立 CARGO_HOME 避免锁冲突
