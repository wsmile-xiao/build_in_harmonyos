# cifer

**软件描述**: cifer 是一个经典密码破解工具，提供多种经典密码的分析和破解功能，包括仿射密码、培根密码、维吉尼亚密码、列置换密码、频率分析等。以交互式 shell 形式运行，支持脚本执行。

**主页**: https://code.google.com/archive/p/cifer/
**许可证**: GPL-3.0-or-later
**作者**: Simrun Basuita & Daniel Richman (2008)

## 版本

| 版本 | 状态 | 构建系统 | 编译器 |
|------|------|---------|--------|
| 1.2.0 | built | makefile | clang 15.0.4 |

## 依赖

- readline 8.2 (预编译包已安装)

## 平台适配要点

- Makefile 硬编码 `CC = gcc`，需通过命令行覆盖为 `CC=clang`
- readline 头文件在非标准路径 `$DEFAULT_PREFIX/include/`，需添加 `-I` 选项
- 已知上游 bug: `file2buffer` 函数在 AArch64 平台上因 char 无符号导致 EOF 检测失败
