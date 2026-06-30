# sqlcmd

> Microsoft sqlcmd — SQL Server 命令行工具

## 简介

sqlcmd 是 Microsoft 提供的 SQL Server 命令行工具，允许用户从命令行连接 SQL Server 并执行查询、脚本和管理操作。这是新版 Go 实现的 sqlcmd（modern 版本）。

## OHOS 适配要点

- Go 项目，因 HarmonyOS HMDFS fallocate 限制无法本地编译 Go linker
- 使用官方预编译 linux-arm64 二进制 + ELF 签名适配
- 无源码补丁，仅需 sign-elf 签名

## 排除与替代

- 本地 Go 编译因 HMDFS fallocate/mmap 限制失败，使用预编译二进制替代

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| goenv | 3.1.1 | Go 版本管理（编译尝试） |

## 功能验证

```bash
sqlcmd --version
```

## 参考

- [官方文档](https://learn.microsoft.com/en-us/sql/tools/sqlcmd/sqlcmd-utility)
- [源码仓库](https://github.com/microsoft/go-sqlcmd)
