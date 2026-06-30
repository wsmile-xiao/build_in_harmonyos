# viu v1.6.1 适配笔记

## 编译环境
- 构建系统: cargo (Rust)
- 编译日期: 2026-05-26
- 编译器: rustc 1.95.0 (clang/clang++ for native deps)
- 状态: built

## 编译步骤

1. 下载源码并解压到 work 目录
2. 修复 cargo 二进制 RUNPATH（patchelf + sign-elf），使其能在 OHOS musl ldso 上加载 libz.so
3. 使用独立 CARGO_HOME 避免 lock 冲突
4. `cargo build --release` 编译
5. 复制 target/release/viu 到 staging 目录并签名

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cargo 无法加载 libz.so | OHOS musl ldso namespace 机制不搜索用户目录 | patchelf 修改 RUNPATH + sign-elf 签名 |
| 2 | cargo 阻塞等待 file lock | 并行构建共享 .cargo 目录 | 使用独立 CARGO_HOME |

## 源码修改

无源码修改，viu 可直接编译。

## 依赖版本

- rust/1.95.0
- zlib (系统预编译包)

## 验证结果

```bash
$ viu --version
viu 1.6.1
```

## 注意事项

- Rust 项目编译需要先修复 cargo 的 RUNPATH
- 并行编译时必须使用独立 CARGO_HOME
---

**编译结束**: 2026-05-26 17:09
**最终状态**: built
