# czkawka 11.0.1 — 编译笔记

## 概述
czkawka 是一个 Rust 编写的重复文件查找工具。本项目使用 cargo 编译 czkawka_cli 子 crate。

## 编译过程
1. **初始化**: `ohc-run.py init-build czkawka 11.0.1 --url=https://github.com/qarmin/czkawka/archive/refs/tags/11.0.1.tar.gz`
2. **Rust工具链修复**: cargo 和 rustc 需要修复 RPATH 和 ELF 签名才能在 OpenHarmony 上运行
   - 复制 cargo/rustc 到 ~/tmp/rust-bin/
   - 使用 patchelf 添加 /storage/Users/currentUser/usr/local/lib 到 RPATH
   - 使用 ohc-run.py sign-elf 签名
3. **编译**: `cargo build --release -p czkawka_cli` — 耗时 52 分钟
4. **安装**: 复制 czkawka_cli 到 $TEST_PREFIX/$DEFAULT_PREFIX/bin/
5. **RPATH 设置**: 使用 patchelf 设置 RPATH 为 /storage/Users/currentUser/usr/local/lib

## 依赖
- Rust 工具链 (1.95.0) — 需要修复 RPATH 和 ELF 签名
- zlib — cargo 依赖 libz.so（musl linker 需要找到）
- 无额外 C 库依赖

## 问题与解决方案
- cargo 无法加载 libz.so → 使用 patchelf 修改 cargo 的 RPATH + ELF 签名
- 无源码修改 → 不需要补丁

## 编译结果
- 二进制: czkawka_cli (39.8MB)
- 版本: czkawka 11.0.1

**编译开始**: 2026-05-26 15:46
**编译结束**: 2026-05-26 17:33
**最终状态**: built
---

**编译结束**: 2026-05-26 17:36
**最终状态**: built
