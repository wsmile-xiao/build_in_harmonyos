# dcfldd 1.9.3 — OpenHarmony 预编译包

## 软件简介

dcfldd 是 dd 命令的增强版本，专为取证和安全领域设计。它在标准 dd 基础上增加了哈希校验（md5/sha1/sha256/sha384/sha512）、分块写入、进度显示、并行写入等功能。

- **名称**: dcfldd
- **版本**: 1.9.3
- **许可证**: GPL-2.0-or-later
- **源码**: https://github.com/resurrecting-open-source-projects/dcfldd
- **语言**: C
- **构建系统**: autotools

## 平台信息

- **目标平台**: aarch64-unknown-linux-ohos (OpenHarmony)
- **编译器**: clang/clang++
- **构建日期**: 2026-06-06

## 安装产物

| 文件 | 路径 |
|------|------|
| dcfldd 可执行文件 | /storage/Users/currentUser/usr/local/bin/dcfldd |
| man 手册 | /storage/Users/currentUser/usr/local/share/man/man1/dcfldd.1 |

## 使用方式

```bash
# 基本数据复制
dcfldd if=input.bin of=output.bin bs=4096

# 带 MD5 哈希校验
dcfldd if=input.bin of=output.bin md5log=hash.md5

# 分块写入（每块 1MB）
dcfldd if=large.bin of=chunk. bs=1M split=1048576

# 显示进度
dcfldd if=input.bin of=output.bin statusinterval=10
```

## 验证

```bash
dcfldd --version
# 输出: dcfldd (dcfldd) 1.9.3
```

## 适配补丁

1 个补丁 (0001-configure.ac.patch): 移除 PKG_PROG_PKG_CONFIG 和 PKG_CHECK_MODULES 对 bash-completion 的依赖，适用于 pkg.m4 不可用的 OHOS 构建环境。