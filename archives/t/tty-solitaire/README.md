# tty-solitaire

终端 ncurses 纸牌游戏（Klondike Solitaire），在终端中运行经典纸牌游戏。

## 基本信息

| 属性 | 值 |
|------|------|
| 主页 | https://github.com/mpereira/tty-solitaire |
| 许可证 | MIT |
| 语言 | C |
| 构建系统 | plain Makefile |
| 依赖 | ncurses (宽字符版本 ncursesw) |

## 已编译版本

| 版本 | 状态 | 编译日期 | 包大小 |
|------|------|----------|--------|
| 1.4.1 | published | 2026-06-11 | 313KB |

## 关键知识

- ncurses 预编译包不含开发头文件，依赖 ncurses 的软件需从源码手动生成 curses.h
- tty-solitaire 是 plain Makefile 项目，无 configure 脚本，直接 `make CC=clang` 编译
- VERSION 宏需引号包裹 `-DVERSION=\"1.4.1\"`