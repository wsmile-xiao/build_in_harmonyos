# vitetris 0.59.1 — OpenHarmony 预编译包

## 简介

vitetris 是一个终端（命令行）俄罗斯方块游戏，支持单人/双人模式和网络对战。

- **版本**: 0.59.1 (20201226)
- **许可证**: BSD-2-Clause
- **源码**: https://github.com/vicgeralds/vitetris/archive/refs/tags/v0.59.1.tar.gz
- **平台**: OpenHarmony aarch64

## 安装

```bash
# 解压预编译包
tar xzf vitetris-0.59.1-ohos-aarch64.tar.gz -C /path/to/install
# 安装后二进制位于 /path/to/install/storage/Users/currentUser/usr/local/bin/tetris
```

## 使用

```bash
tetris              # 启动游戏（需要终端环境）
tetris -help        # 查看帮助
tetris -help game   # 查看游戏选项
tetris -help term   # 查看终端选项
tetris -hiscores    # 查看高分榜
tetris -nomenu      # 跳过菜单直接开始
```

## 构建信息

- **构建系统**: makefile（自定义 configure 脚本）
- **编译器**: clang 15.0.4 (aarch64-unknown-linux-ohos)
- **SDK**: OpenHarmony SDK 26.0.0.18
- **构建日期**: 2026-06-03
- **依赖**: 仅 libc.so（无外部依赖）
- **二进制格式**: ELF64 AArch64 PIE
- **终端后端**: ansi（非 curses/Xlib）

## 注意事项

- 需要 ELF 签名授权才能在 OpenHarmony 上执行
- 使用 `-help` 而非 `--help` 来获取帮助信息
- 需要终端环境才能正常运行游戏交互界面