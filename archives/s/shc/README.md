# shc — Shell Script Compiler

## 简介

shc（Shell Script Compiler）是一个将 Shell 脚本编译为可执行二进制文件的工具。它通过将 Shell 脚本转换为 C 源码，然后编译为 ELF 二进制，从而实现脚本加密和分发。

- **官网**: https://github.com/neurobin/shc
- **许可证**: GPL-3.0-or-later
- **语言**: C

## 已编译版本

| 版本 | 状态 | 日期 | 构建系统 | 补丁数 |
|------|------|------|----------|--------|
| 4.0.3 | published | 2026-06-01 | autotools | 1 |

## OpenHarmony 适配要点

- 需移除 configure 脚本中的 `umask 077` 限制（HMDFS 文件系统权限机制导致临时目录不可写入）
- shc 生成的二进制需要 ELF 签名才能在 HMDFS 上执行
- shc 无 `--version` 参数，使用 `-h` 查看版本信息
- 测试套件依赖多种 Shell（/bin/dash、/bin/bash 等），在 OpenHarmony 上因 Shell 缺失无法通过