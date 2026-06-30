# bore-cli 0.6.0 适配笔记

## 编译环境
- 构建系统: cargo (Rust)
- 编译日期: 2026-06-18
- 编译器: rustc 1.95.0 / cargo 1.95.0
- 状态: built

## 编译步骤

1. 通过 crates.io 镜像（rsproxy.cn）下载 bore-cli-0.6.0.crate
2. 使用 `ohc-run.py init-build bore-cli 0.6.0 --url=file://...` 初始化
3. 运行 `cargo update` 更新依赖（修复 socket2 IovLen 问题）
4. 运行 `cargo build --release` 编译
5. 安装到 staging 目录和本地前缀
6. 使用 `ohc-run.py package bore-cli 0.6.0` 打包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | socket2 v0.4.9 编译失败：`IovLen` type not found | socket2 旧版本不兼容 OpenHarmony libc 定义 | `cargo update` 将 socket2 升级到 0.6.4 |
| 2 | ohc-run.py 无法自动搜索 bore-cli 下载 URL | bore-cli 是 Rust crate，不在常规 tarball 搜索引擎中 | 手动从 crates.io 镜像下载 .crate 文件，用 file:// URL |
| 3 | 构建系统检测为 autotools（错误） | 自动检测基于常见构建文件，Rust 项目无 Makefile/configure | 手动在 manifest.yaml 中设置 build_system: cargo |

## 源码修改

无补丁。仅通过 `cargo update` 更新依赖版本，未修改源码本身。

## 依赖版本

- rustc 1.95.0 (2026-04-14)
- cargo 1.95.0 (2026-03-21)
- socket2 0.6.4 (从 0.4.9 升级)
- tokio 1.52.3 (从 1.28.0 升级)
- libc 0.2.186 (从 0.2.142 升级)

## 验证结果

```bash
$ ~/usr/local/bin/bore --version
bore-cli 0.6.0

$ file ~/usr/local/bin/bore
ELF 64-bit LSB pie executable, ARM aarch64, version 1 (SYSV), dynamically linked, interpreter /lib/ld-musl-aarch64.so.1

$ bore --help
bore-cli 0.6.0
Eric Zhang <ekzhang1@gmail.com>
A modern, simple TCP tunnel in Rust that exposes local ports to a remote server, bypassing standard NAT connection firewalls.

USAGE:
    bore <COMMAND>

FLAGS:
    -h, --help       Prints help information
    -V, --version    Prints version information

COMMANDS:
    local    Start a local client that forwards TCP traffic to a remote server
    server   Run the bore server on the remote machine
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bore-cli-0.6.0-ohos-aarch64.tar.gz | 2321KB | 预编译包（含 bore 二进制） |
| bore-cli-0.6.0-ohos-aarch64-debug.tar.gz | 745KB | 调试符号包 |

## 注意事项

- bore-cli 是 Rust 项目，构建命令为 `cargo build --release`，而非 configure/make
- 二进制名为 `bore`（crate 名为 `bore-cli`，但生成的可执行文件名为 `bore`）
- 需要运行 `cargo update` 更新依赖以解决 OpenHarmony 平台兼容性问题
---

**编译结束**: 2026-06-18 01:32
**最终状态**: published
