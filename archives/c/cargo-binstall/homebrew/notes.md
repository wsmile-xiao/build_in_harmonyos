# cargo-binstall homebrew 适配笔记

## 编译环境
- 构建系统: precompiled (Rust binary, rustc SIGSEGV on HarmonyOS → must use precompiled)
- 编译日期: 2026-06-03
- 编译器: N/A (precompiled binary from GitHub)
- 状态: published

## 编译步骤

### 预编译方案（rustc在HarmonyOS上崩溃，无法从源码编译）

1. **下载预编译二进制**: 从 GitHub releases 下载 `cargo-binstall-aarch64-unknown-linux-musl.full.tgz` (v1.19.1)
   - 包含: cargo-binstall, detect-targets, detect-wasi 三个 ELF 二进制
   - 通过 ghfast.top GitHub 代理下载（直连 GitHub SSL 证书验证失败）

2. **DESTDIR 安装 (R20)**:
   ```bash
   mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
   cp cargo-binstall detect-targets detect-wasi $TEST_PREFIX/$DEFAULT_PREFIX/bin/
   ```

3. **ELF 签名**: 使用 binary-sign-tool sign -selfSign 1 对三个二进制签名
   - 需先 $OBJCOPY --remove-section .codesign 清理旧签名段

4. **本地安装**: cp 到 $DEFAULT_PREFIX/bin/ 并重新签名验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Rust musl静态二进制预期SIGSEGV | 旧版HarmonyOS kernel不支持静态musl | ⚠️ 实测：Kernel 1.12.0 上静态musl二进制可正常运行！task警告已过时 |
| 2 | GitHub直连SSL证书验证失败 | 鸿蒙Python缺少CA证书 | 设置 SSL_CERT_FILE=/storage/Users/currentUser/usr/local/ssl/cert.pem + ghfast.top代理 |
| 3 | GNU动态二进制需要glibc | 系统只有musl libc | 优先使用静态musl版本（实测可用）；GNU版本需要glibc compat层 |

## 依赖版本

- 无编译依赖（预编译二进制）
- 运行时依赖: musl libc (系统自带 /lib/ld-musl-aarch64.so.1)

## 验证结果

```bash
$ cargo-binstall -V
1.19.1

$ detect-targets
aarch64-unknown-linux-musl

$ detect-wasi
WASI is not runnable
```

所有三个二进制均正常工作，已ELF签名。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| cargo-binstall | ~15MB | Rust binary installer 主程序 |
| detect-targets | ~573KB | 目标平台检测辅助程序 |
| detect-wasi | ~377KB | WASI运行时检测辅助程序 |

## 注意事项

- ⚠️ **关于SIGSEGV警告**: 任务描述称"Rust musl静态二进制全部SIGSEGV"，但实测在 HarmonyOS Kernel 1.12.0 上 cargo-binstall v1.19.1 的 aarch64-unknown-linux-musl 静态二进制运行正常。这可能是因为新版 kernel 已修复相关问题。
- cargo-binstall 需要 cargo 环境才能实际安装crate（它本身只是安装工具，不依赖 cargo 运行）
- detect-targets 和 detect-wasi 是 cargo-binstall 内部使用的辅助二进制，必须一起安装
---

**编译结束**: 2026-06-03 12:00
**最终状态**: published
