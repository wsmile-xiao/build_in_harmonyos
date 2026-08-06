# dua-cli 2.34.0 适配笔记

## 编译环境
- 构建系统: cargo (Rust)
- 编译日期: 2026-08-06
- 编译器: clang 15.0.4 (OHOS HNP)
- Rust 版本: 1.97.1 (Harmonybrew)
- 状态: published (Conan 配方已验证)

## 编译步骤

### Rust 工具链安装

通过 Harmonybrew 安装 Rust 工具链：
```bash
zsh -c "$(curl -fsSL https://harmonybrew.atomgit.com/install.sh)"
eval "$(/storage/Users/currentUser/.harmonybrew/bin/brew shellenv)"
brew install rust
```

### 从源码编译

```bash
export CC=clang CXX=clang++ CFLAGS="-fPIC -O2"
export TMPDIR=$HOME/tmp
cd dua-cli-2.34.0
cargo build --release
```

编译成功，生成 `target/release/dua` 二进制文件（3.1MB，动态链接 musl）。

### 验证

```bash
$ dua --version
dua 2.34.0

$ dua aggregate ~/tmp/builds/dua-cli-2.34.0.work/src/
   8.00 KiB config.rs
   ...
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | rustc 在 OpenHarmony 上 SIGSEGV 崩溃 | 历史问题：旧版 rustc 加载 librustc_driver.so 时崩溃 | 使用 Harmonybrew 安装的 Rust 1.97.1，已修复此问题 |
| 2 | cargo build 报 "linker cc not found" | OHOS 上没有 cc 符号链接 | 设置 CC=clang 环境变量 |
| 3 | GitHub musl 预编译二进制无法执行 | SELinux 安全上下文 hmdfs:s0 不允许执行 | 从源码编译，Harmonybrew Rust 生成的二进制可正常运行 |

## 依赖版本

无额外依赖（dua-cli 的 Rust 依赖由 cargo 自动管理，不需要 Conan 依赖）

## 历史对比

| 项目 | 2026-06-04 (旧) | 2026-08-06 (新) |
|------|-----------------|-----------------|
| 构建方式 | 预编译二进制 | 从源码编译 (cargo) |
| Rust 可用性 | 不可用 (SIGSEGV) | 可用 (Harmonybrew 1.97.1) |
| 二进制大小 | 2.3MB (静态) | 3.1MB (动态 musl) |
| Conan 配方 | 无 | 有 (conanfile.py + test_package) |
| 软件裁剪 | N/A (预编译) | 无裁剪 (完整从源码编译) |

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (cargo 构建) |
| conandata.yml | 源码 URL + SHA256 |
| test_package/ | 测试包 (test.sh smoke test) |
| commands.json | 命令行工具声明 |
| manifest.yaml | 版本元数据 |
---

**编译结束**: 2026-08-06 08:34
**最终状态**: published
