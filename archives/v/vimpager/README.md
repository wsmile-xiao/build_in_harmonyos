# vimpager

使用 Vim 作为分页器（less 替代工具）。

vimpager 是一个 shell 脚本，将 Vim 用作终端分页器，提供语法高亮、更好的搜索功能以及 Vim 的全部特性来查看文件。同时包含 vimcat 工具，用于在终端中显示带语法高亮的文件内容。

- 许可证：BSD-2-Clause
- 语言：Shell 脚本（无需 C/C++ 编译）
- 构建系统：纯 Makefile（非 autotools，无 configure 脚本）
- 主页：https://github.com/rkitover/vimpager

## 鸿蒙适配说明

- 构建过程仅需 `make PREFIX=$DEFAULT_PREFIX`，无需 configure 步骤
- 安装使用 DESTDIR 模式：`make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX`
- /tmp 为只读文件系统（E002 陷阱），需使用 $TMPDIR
- pandoc 不可用时跳过 man 页面生成，不影响核心功能

## 可用版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 2.06 | published | 2026-06-16 |
