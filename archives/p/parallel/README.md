# parallel

> GNU parallel — 在多个核心上并行执行 shell 命令

## 简介

GNU parallel 是一个 shell 工具，用于在本地或远程计算机上并行执行作业。作业可以是一条命令或一个读取输入的小脚本。典型的输入是一行文件、一行URL或一行文件列表。

## OHOS 适配要点

- autotools 构建系统，`./configure && make && make install` 标准流程
- Makefile.in 中硬编码 `SHELL=/bin/bash`，需改为 `SHELL=@SHELL@`（HarmonyOS 使用 musl sh）
- 纯 Perl 脚本工具，无 ELF 二进制文件，无需签名/strip/RPATH

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| Perl | 系统自带 | 运行时依赖 |

## 功能验证

```bash
parallel --version
```

## 参考

- [官方文档](https://www.gnu.org/software/parallel/)
- [源码仓库](https://ftp.gnu.org/gnu/parallel/)
