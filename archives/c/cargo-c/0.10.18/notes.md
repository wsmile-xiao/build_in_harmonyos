# cargo-c 0.10.18 适配笔记

## 编译环境
- 构建系统: cargo (Rust)
- 编译日期: 2026-06-17
- 编译器: clang/clang++ (系统C/C++), rustc 1.95.0 (Rust)
- 状态: built

## 编译步骤

1. 从 GitHub 下载源码: https://github.com/lu-zero/cargo-c/archive/refs/tags/v0.10.18.tar.gz
2. 修正 init-build 的嵌套源码检测误判（将 example-project/usage-from-c 子目录提升为根目录的错误），重新解压并手动设置 work 目录
3. 设置环境变量:
   - `PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig`
   - `OPENSSL_DIR=/storage/Users/currentUser/usr/local`
4. 编译: `cargo build --release`
5. 安装到 staging 目录: 手动复制 cargo-capi/cargo-cbuild/cargo-cinstall/cargo-ctest 到 `$TEST_PREFIX/bin/`
6. 安装到本地: 复制四进制到 `$DEFAULT_PREFIX/bin/`
7. ELF 签名: `ohc-run.py sign-elf` 对所有二进制签名
8. 打包: `ohc-run.py package cargo-c 0.10.18`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 嵌套源码检测误将 example-project/usage-from-c 提升为根目录 | 该子目录含 Makefile/meson.build/run_tests.c，被误判为主源码 | 手动重新解压 tarball，将正确根目录内容移到 orig/work |
| 2 | openssl-sys 编译失败：找不到 OpenSSL | PKG_CONFIG_PATH 未包含本地 pkgconfig 目录，OPENSSL_DIR 未设置 | 设置 PKG_CONFIG_PATH 和 OPENSSL_DIR 指向 ~/usr/local |

## 源码修改

无源码修改，无补丁。

## 依赖版本

- openssl 3.5.6 (本地预编译包)
- curl 8.8.0 (本地预编译包)
- rust 1.95.0 (系统)
- clang 15.0.4 (系统)
- libgit2 (cargo 内嵌编译 libgit2-sys 0.18.5+1.9.4)
- libssh2 (cargo 内嵌编译 libssh2-sys 0.3.1)
- libz (cargo 内嵌编译 libz-sys 1.1.29)

## 验证结果

```bash
$ cargo-capi --version
cargo-c 0.10.18+cargo-0.92.0
$ cargo-cbuild --version
cargo-c 0.10.18+cargo-0.92.0
$ cargo-cinstall --version
cargo-c 0.10.18+cargo-0.92.0
$ cargo-ctest --version
cargo-c 0.10.18+cargo-0.92.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| cargo-c-0.10.18-ohos-aarch64.tar.gz | ~128MB | 预编译包（4个cargo子命令二进制） |
| cargo-c-0.10.18-ohos-aarch64-debug.tar.gz | ~34MB | 调试符号 |

## 注意事项

- cargo-c 是 cargo 子命令工具集，产出4个二进制: cargo-capi, cargo-cbuild, cargo-cinstall, cargo-ctest
- 编译需要 Rust 环境 (rustc >= 1.89)，本系统已有 rustc 1.95.0
- 需要设置 PKG_CONFIG_PATH 和 OPENSSL_DIR 环境变量才能找到 OpenSSL
- init-build 的嵌套源码检测可能误判（本例中误将 example-project/usage-from-c 视为主源码），需人工检查
---

**编译结束**: 2026-06-17 06:07
**最终状态**: built
