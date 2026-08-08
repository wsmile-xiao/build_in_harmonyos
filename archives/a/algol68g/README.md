# Algol 68 Genie (algol68g)

> Algol 68 语言编译器-解释器，执行 Algol 68 程序（命令行工具 a68g）

## 简介

Algol 68 Genie (algol68g) 是 Algol 68 语言的一个完整实现，采用编译-解释（compiler-interpreter）方式运行。它由 Marcel van der Veer 从零编写，支持部分参数化、并行的与子句、任意精度算术、FFT、正则表达式等特性，是 Algol 68 语言最完整的实现之一。

本项目将 algol68g 3.1.2 适配到 HarmonyOS PC 平台（arm64），提供 `a68g` 命令行工具。

## OHOS 适配要点

- **config.guess/config.sub**：上游 2018 版无法识别 HarmonyOS（`uname -s` 返回 HarmonyOS），已升级至 2023 版并添加 `aarch64-unknown-linux-ohos` 三元组支持（E007）
- **configure umask**：config.status 创建临时目录使用 `umask 077`，在 HMDFS 上 0700 目录不可写（SELinux 限制 chmod），已改为 `umask 002`（E046 平台限制）
- 可选依赖 GSL/MPFR/curses/PostgreSQL 未启用，基础功能不受影响

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| 无 | - | 纯 C 实现，无第三方库依赖 |

## 功能验证

```bash
a68g --version
a68g --execute 'print((1+1))'   # 输出 +2
make check                      # 上游 24 个测试全部通过
```

## 参考

- [Algol 68 Genie 官网](https://algol68genie.nl/)
- [源码仓库](https://algol68genie.nl/algol68g-3.1.2.tar.gz)
