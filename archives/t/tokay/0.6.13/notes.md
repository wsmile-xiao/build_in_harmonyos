# tokay 0.6.13 适配笔记

## 编译环境
- 构建系统: cargo
- 编译日期: 2026-05-27
- 编译器: rustc 1.95.0
- 目标平台: OHOS aarch64
- 状态: built

## 编译步骤

### 1. 源码获取
```bash
git clone https://ghfast.top/https://github.com/tokay-lang/tokay.git
cd tokay
git checkout v0.6.13
```

### 2. 环境变量设置
```bash
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
export PATH=$HOME/usr/local/bin:$PATH
export SSL_CERT_FILE=$HOME/usr/local/ssl/cert.pem
export CARGO_HTTP_CAINFO=$HOME/usr/local/ssl/cert.pem
```

### 3. Cargo 镜像配置 (~/.cargo/config.toml)
```toml
[source.crates-io]
replace-with = 'ustc'

[source.ustc]
registry = "sparse+https://mirrors.ustc.edu.cn/crates.io-index/"
```

### 4. 编译
```bash
cargo build --release
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | rustc 权限问题 | OHOS 要求 ELF 二进制签名 | 使用 ohc-run.py sign-elf 签名 |
| 2 | cargo 无法下载依赖 | SSL 证书问题 | 设置 SSL_CERT_FILE 和 CARGO_HTTP_CAINFO |
| 3 | nix 0.20.2 编译错误 | 缺少 OHOS 兼容性条件编译 | 添加 target_env = "ohos" 条件 |
| 4 | nix 0.29.0 编译错误 | ioctl_num_type 类型不匹配 | 添加 target_env = "ohos" 条件 |

## 源码修改

### nix 0.20.2 补丁

修改了以下文件，添加 `not(target_env = "ohos")` 条件：

- `src/fcntl.rs`: O_FSYNC/O_DSYNC
- `src/lib.rs`: mqueue 模块
- `src/sys/mod.rs`: aio/personality/statfs/timer 模块
- `src/sys/statvfs.rs`: ST_* flags
- `src/sys/socket/mod.rs`: cmsg_len
- `src/sys/signal.rs`: SigevThreadId
- `src/sys/ptrace/linux.rs`: Request enum
- `src/sys/ioctl/linux.rs`: ioctl_num_type

### nix 0.29.0 补丁

- `src/sys/ioctl/linux.rs`: ioctl_num_type 类型

## 依赖版本

- Rust: 1.95.0
- OpenSSL: 3.5.6

## 验证结果

```bash
$ ./tokay --version
Tokay 0.6.13
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| tokay-0.6.13-ohos-aarch64.tar.gz | 4.8MB | Release 版本预编译包 |
| tokay-0.6.13-ohos-aarch64-debug.tar.gz | 1.2MB | Debug 符号包 |

## 注意事项

1. Rust 项目需要先对 rustc 和相关库签名才能在 OHOS 上运行
2. nix crate 需要针对 OHOS 添加兼容性补丁
3. 使用国内镜像加速 cargo 下载
---
**编译结束**: 2026-05-27 18:02
**最终状态**: built