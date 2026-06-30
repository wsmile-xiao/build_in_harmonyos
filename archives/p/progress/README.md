# progress — Coreutils Progress Viewer

## 简介

progress（原名 cv）是一个 Linux 系统下的命令行工具，用于实时监控 coreutils 工具（如 cp、mv、dd、tar、rsync 等）的文件操作进度。它可以显示已复制/已处理的百分比、传输速率和预计剩余时间。

## 官方信息

- **作者**: Xfennec
- **许可证**: GPL-3.0-or-later
- **主页**: https://github.com/Xfennec/progress
- **源码**: https://github.com/Xfennec/progress/archive/refs/tags/v0.17.tar.gz

## 已编译版本

| 版本 | 状态 | 日期 | 构建系统 |
|------|------|------|----------|
| 0.17 | published | 2026-06-01 | makefile |

## 依赖

- ncurses/6.5（静态库 libncursesw.a，用于终端界面显示）

## 特性

- 监控 cp、mv、dd、tar、rsync、scp、grep 等命令的进度
- 显示百分比、传输速率、预计剩余时间
- 支持监控特定 PID 或命令
- 支持连续监控模式（-m 参数）
- 提供 zsh 补全脚本

## OpenHarmony 适配说明

- 纯 Makefile 项目，无 configure 脚本
- Makefile 已原生支持 HarmonyOS 平台检测（`ifeq ($(UNAME), HarmonyOS)`）
- 需要两个补丁：0001-Makefile.patch（PREFIX 定义位置调整）和 0002-configure.patch（configure wrapper）
- 链接 ncursesw 静态库用于终端界面

## 安装验证

```bash
progress --version   # 输出: progress version 0.17
progress -h          # 显示完整帮助信息
```