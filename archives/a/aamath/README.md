# aamath — ASCII 艺术数学表达式渲染器

aamath 是一个将数学表达式渲染为 ASCII 艺术文本格式的小型命令行工具。它可以将常见的数学符号（根号、积分、分数、连分数、矩阵等）以纯文本 ASCII 字符绘出，适合在终端或纯文本环境中展示数学公式。

## 功能概述

- 将数学表达式渲染为 ASCII 艺术格式
- 支持根号、积分、分数、连分数、矩阵、极限、级数等
- 交互式模式（依赖 readline）和非交互式模式
- 命令行直接传入表达式，或从管道/文件读取
- `-r` 参数切换窄根号模式，`-q` 参数切换静默模式

## OHOS 适配要点

- **无 configure 脚本**：项目是纯 Makefile 构建系统，无 autotools configure
- **编译器替换**：需要将 Makefile 中 g++ 替换为 clang++
- **termcap 替换**：OpenHarmony 无 libtermcap，需用 -lncurses 替代
- **readline 头文件路径**：需添加 -I$DEFAULT_PREFIX/include 以找到 readline 头文件
- **bison/flex 生成文件**：bison 3.8+ 生成 parser.tab.c/parser.tab.h（而非 y.tab.c/y.tab.h），需适配 Makefile 规则
- **DESTDIR 支持**：原始 Makefile 无 install target 和 DESTDIR 支持，需手动添加

## 依赖关系

### 编译依赖
- readline 8.2（提供交互式输入和历史功能）
- ncurses 6.5（提供终端控制功能，替代 termcap）
- bison 3.8.2（生成 parser）
- flex 2.6.4（生成 lexer）

### 运行依赖
- libreadline.so.8（交互式模式）
- libc++_shared.so（C++ 运行时库）
- libc.so（系统 libc）

## 参考资料

- 官网：无独立官网
- 源码：https://cdn.netbsd.org/pub/pkgsrc/distfiles/aamath-0.3.tar.gz
- 作者：Mauro Persano (mauro_persano at yahoo dot com)
- 许可证：GPLv2
