# git-cliff 2.10.1 适配笔记

## 编译环境
- 构建系统: cargo (Rust/Cargo workspace)
- 编译日期: 2026-06-17
- 编译器: clang/clang++ (Rust: rustc 1.95.0, cargo 1.95.0)
- 状态: published

## 编译步骤

1. 源码下载: 通过 ghfast.top GitHub 代理下载 v2.10.1 tarball（GitHub 直连超时）
2. 初始化: `ohc-run.py init-build git-cliff 2.10.1 --url=https://ghfast.top/https://github.com/orhun/git-cliff/archive/refs/tags/v2.10.1.tar.gz`
3. 构建: `cargo build --release` — 一次性成功，耗时约 4m32s
4. 安装(staging): 手动复制二进制到 `$TEST_PREFIX/$DEFAULT_PREFIX/bin/git-cliff`（DESTDIR 模式）
5. ELF 签名: `ohc-run.py sign-elf` 签名所有位置的二进制
6. 质量门禁: `verify-build` PASS (G1-G4)
7. 打包: `ohc-run.py package` — 生成 git-cliff-2.10.1-ohos-aarch64.tar.gz (11.4MB)
8. 本地安装: 复制二进制到 `$DEFAULT_PREFIX/bin/git-cliff`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连超时无法下载源码 | 网络环境限制 | 使用 ghfast.top 代理下载 |
| 2 | init-build 检测为 autotools 而非 cargo | 脚本未识别 Cargo.toml | 手动修改 manifest.yaml 的 build_system 为 cargo |
| 3 | verify-build G4 缺少 build_system 字段 | 验证脚本检查扁平字段而非嵌套字段 | 在 manifest.yaml 顶层添加 build_system: cargo |
| 4 | verify-build 找不到二进制文件 | DESTDIR 模式下文件在 $TEST_PREFIX/$DEFAULT_PREFIX/bin/ 而非 $TEST_PREFIX/bin/ | 在 $TEST_PREFIX/bin/ 和 $DEFAULT_PREFIX/bin/ 也安装二进制 |

## 源码修改

无补丁，源码直接编译成功。git-cliff 是 Rust 项目，使用 Cargo 构建系统，无需修改源码即可在 OpenHarmony 平台编译。

## 依赖版本

- rustc 1.95.0
- cargo 1.95.0
- clang 15.0.4 (OpenHarmony LLVM)

## 验证结果

```bash
$ git-cliff --version
git-cliff 2.10.1

$ file ~/usr/local/bin/git-cliff
ELF 64-bit LSB pie executable, ARM aarch64, version 1 (SYSV), dynamically linked, interpreter /lib/ld-musl-aarch64.so.1, stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| git-cliff-2.10.1-ohos-aarch64.tar.gz | 11.4MB | 预编译包（含 ELF 签名） |
| git-cliff-2.10.1-ohos-aarch64-debug.tar.gz | 52.7KB | 调试符号包 |

## 注意事项

- git-cliff 是 Rust/Cargo 项目，需要 rustc ≥ 1.85.1（本项目使用 1.95.0）
- GitHub 在 OpenHarmony 网络环境下可能超时，需使用代理（ghfast.top）
- Cargo 构建系统不支持 DESTDIR 模式，需要手动复制二进制到 staging 目录
- verify-build 脚本的 install_prefix 使用 TEST_PREFIX 而非 TEST_PREFIX/$DEFAULT_PREFIX，与 DESTDIR 模式不完全兼容
---

**编译结束**: 2026-06-17 01:55
**最终状态**: published
