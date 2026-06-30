# resvg 0.47.0 — 编译笔记

## 概述
resvg 是 Rust 编写的 SVG 渲染库和命令行工具。本项目使用 cargo 编译 resvg 二进制。

## 编译过程
1. **初始化**: `ohc-run.py init-build resvg 0.47.0 --url=https://github.com/linebender/resvg/archive/refs/tags/v0.47.0.tar.gz`
   - GitHub 下载超时，使用 ghfast.top 镜像下载源码
2. **Rust工具链修复**: cargo 和 rustc 需要修复 RPATH 和 ELF 签名才能在 OpenHarmony 上运行
   - 使用 ~/tmp/rust-bin/ 中已 patchelf 处理过的 cargo/rustc（RPATH 已添加 ~/usr/local/lib）
   - 使用 ohc-run.py sign-elf 签名
3. **编译**: `cargo build --release` — 耗时约 51 秒
   - 使用默认 features（text, system-fonts, memmap-fonts, raster-images）
4. **安装**: 复制 resvg 到 $TEST_PREFIX/bin/
5. **ELF 签名**: 使用 ohc-run.py sign-elf 签名二进制

## 依赖
- Rust 工具链 (1.95.0) — 需要修复 RPATH 和 ELF 签名（使用 ~/tmp/rust-bin/ 中已 patch 的版本）
- zlib — cargo 依赖 libz.so（musl linker 需要找到）
- 无源码修改 → 不需要补丁

## 问题与解决方案
- GitHub 下载超时 → 使用 ghfast.top 镜像
- cargo 无法加载 libz.so → 使用 ~/tmp/rust-bin/ 中已 patch RPATH 的 cargo
- 无源码修改 → 不需要补丁

## 验证结果
```bash
$ resvg --version
0.47.0
$ resvg test.svg test.png  # SVG 渲染成功
```

## 编译结果
- 二进制: resvg (4.0MB)
- 版本: resvg 0.47.0

**编译开始**: 2026-05-26 21:22
**编译结束**: 2026-05-26 21:23
**最终状态**: built
---

**编译结束**: 2026-05-26 21:27
**最终状态**: built
