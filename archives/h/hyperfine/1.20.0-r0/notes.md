# hyperfine 1.20.0-r0 适配笔记

## 编译环境
- 构建系统: Rust (Cargo) — 但 rustc 在 musl 平台上 SIGSEGV，无法源码编译
- 编译日期: 2026-06-02
- 编译器: N/A (使用预编译二进制)
- 状态: published

## 编译步骤

由于 rustc 在鸿蒙 musl 平台上崩溃 (SIGSEGV)，采用预编译二进制策略：

1. 从 Alpine Linux edge/community 下载 aarch64 musl APK: `hyperfine-1.20.0-r0.apk`
2. 解压 APK (tar.gz)，提取 `usr/bin/hyperfine` 二进制
3. 从 GitHub releases 提取补全文件和 man 页面
4. 安装到 DESTDIR staging 目录 (`$TEST_PREFIX/$DEFAULT_PREFIX/`)
5. ELF 签名 (`ohc-run.py sign-elf`)
6. 验证二进制可执行: `hyperfine --version` → `hyperfine 1.20.0`
7. 打包为 tar.gz 预编译包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | rustc SIGSEGV on musl | 鸿蒙 musl 平台不支持 Rust 编译器 | 使用 Alpine Linux 预编译 aarch64 musl 二进制 |
| 2 | GitHub releases 缺少 aarch64-musl variant | hyperfine CI 只编译 x86_64-musl 和 arm-musleabihf | 从 Alpine Linux APK 获取 aarch64 musl 二进制 |
| 3 | ELF 签名要求 | 鸖蒙安全机制 | `ohc-run.py sign-elf` 签名后二进制可执行 |

## 依赖版本

- musl libc: /lib/ld-musl-aarch64.so.1 (系统内置)
- libgcc_s.so.1: ~/usr/local/lib/libgcc_s.so.1 (已预装)

## 验证结果

```bash
$ hyperfine --version
hyperfine 1.20.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/hyperfine | 800KB | ELF signed aarch64 musl 二进制 |
| share/man/man1/hyperfine.1 | 10KB | man 页面 |
| share/bash-completion/completions/hyperfine | 9KB | bash 补全 |
| share/zsh/site-functions/_hyperfine | 14KB | zsh 补全 |
| share/fish/vendor_completions.d/hyperfine.fish | 9KB | fish 补全 |

## 注意事项

- 此二进制为 Alpine Linux 预编译，动态链接 musl libc，需系统提供 /lib/ld-musl-aarch64.so.1 和 libgcc_s.so.1
- 不可源码编译，未来版本升级需继续使用 Alpine 预编译方案
---

**编译结束**: 2026-06-02 02:42
**最终状态**: published
