# nbsdgames

## 简介
nbsdgames 是一个包含 21 个终端文本游戏的集合，包括扫雷、数独、贪吃蛇、拼图等经典游戏，全部基于 C 语言和 ncurses 库实现。

## 主要功能
- 21 种终端文本游戏
- 基于 ncurses 的终端界面
- 轻量级，无外部依赖（仅需 ncurses）

## OHOS 适配
- 构建系统：Makefile
- 目标架构：aarch64-linux-ohos
- 依赖：ncurses（静态链接）

## 依赖
- ncurses
- pkgconf（构建工具）

## 功能验证
```bash
nbsdgames
sudoku -h
minesweeper -h
```

## 参考
- 主页：https://github.com/abakh/nbsdgames
- 源码：https://github.com/abakh/nbsdgames
