# oksh — OpenBSD Ksh 的移植版本

oksh 是基于 OpenBSD ksh 的便携式 shell 实现，提供 ksh88/ksh93 兼容的命令行交互体验，
包括 emacs/vi 行编辑模式、命令历史、别名、函数、管道、重定向等标准 shell 功能。

## 已编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 7.8 | published | 2026-06-16 |

## HarmonyOS 平台适配要点

- configure 自动检测 HarmonyOS，无需源码修改或补丁
- 因未检测到 ncurses 库，编译为无屏幕清除支持模式（不影响核心 shell 功能）
- 二进制需 ELF 签名后方可执行（HarmonyOS 安全机制）
- 无外部库依赖，仅依赖 musl libc

## 来源

- 上游项目: https://github.com/ibara/oksh
- 许可证: ISC/BSD-style
