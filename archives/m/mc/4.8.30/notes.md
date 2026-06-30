# Midnight Commander 4.8.30 编译笔记

## 编译环境
- 编译器: clang
- 构建系统: autotools
- HMDFS 文件系统需使用固定临时目录

## 依赖
- glib 2.88.0
- ncurses 6.4 (需手动添加 KEY_* 定义)
- libintl
- pcre2

## 问题解决
1. HMDFS 限制: config.status 无法在当前目录创建临时文件，需使用 ~/tmp/mc-config-tmp
2. ncurses KEY_* 定义缺失: 手动添加到 curses.h
3. 静态链接: 需手动链接 libglib-2.0.a 和 libintl.a
