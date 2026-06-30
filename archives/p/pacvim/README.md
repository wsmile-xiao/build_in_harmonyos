# PacVim — Vim命令学习游戏

## 简介

PacVim 是一款受 PacMan 启发的游戏，通过在迷宫中操控角色来学习 Vim 的移动和操作命令。玩家需要使用 Vim 键位（h/j/k/l 等）在迷宫中移动，躲避幽灵并收集点数。

- **主页**: https://github.com/jmoon018/PacVim
- **许可证**: LGPL-3.0-or-later
- **语言**: C++ (C++11)
- **构建系统**: Makefile（简单Makefile，无configure脚本）

## 运行方式

```bash
pacvim [难度等级]
# 难度等级: 0~99（0最简单）
# 例如: pacvim 8
```

## 依赖

- ncurses — 终端界面渲染库（鸿蒙平台需预编译包安装）

## 鸿蒙平台编译要点

1. ncurses 仅提供 curses.h（无 wide-char 版 cursesw.h），需替换源码中的 cursesw.h
2. clang++ 默认搜索路径不包含 ~/usr/local/include，需显式 -I 参数
3. Makefile 需添加 DESTDIR 支持、CXX/PREFIX 可覆盖、EXTRA_INC/EXTRA_LIB 变量
