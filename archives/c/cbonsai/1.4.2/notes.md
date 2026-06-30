# cbonsai 1.4.2 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-17
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 源码下载: `https://codeload.github.com/hortinstein/cbonsai/tar.gz/master`
2. 设置 PKG_CONFIG_PATH 指向 ncursesw 和 panelw 的 pkg-config 文件
3. 创建 panelw.pc 和 panel.pc pkg-config 文件（panel库已安装但缺 .pc 文件）
4. 修改 Makefile: CFLAGS 增加 `$(shell pkg-config --cflags ncursesw panelw)`，LDLIBS 改为 `$(shell pkg-config --libs panelw)`（修正库链接顺序 -lpanelw -lncursesw）
5. `make PREFIX=$DEFAULT_PREFIX` 编译
6. `make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX` 安装到 staging 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | panel.h 找不到 | panel.h 位于 ncursesw/ 子目录，pkg-config 未返回 CFLAGS | 修改 Makefile CFLAGS 增加 pkg-config --cflags ncursesw panelw |
| 2 | pkg-config 找不到 ncurses 和 panel | PKG_CONFIG_PATH 未设置 + 缺少 panel.pc | 设置 PKG_CONFIG_PATH 并创建 panelw.pc/panel.pc |
| 3 | _nc_panelhook_sp 未定义 | 静态链接时 -lncursesw -lpanelw 顺序错误（panel依赖ncurses） | 修改 LDLIBS 使用 pkg-config --libs panelw（自动正确排列依赖顺序） |

## 源码修改

- Makefile: 修改 CFLAGS 和 LDLIBS 以适配 ncursesw/panelw pkg-config 配置

## 依赖版本

- ncurses 6.5（已预编译，静态库 --without-shared）

## 验证结果

```bash
$ ./cbonsai --help
Usage: cbonsai [OPTION]...
cbonsai is a beautifully random bonsai tree generator.
✅ Binary works correctly
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| cbonsai | 280960 | ELF 64-bit LSB PIE executable, ARM aarch64 |

## 注意事项

- cbonsai 无 configure 脚本，纯 Makefile 项目
- 静态链接 ncursesw 和 panelw（R4: ncurses --without-shared）
- panel.h 位于 ncursesw/ 子目录，需要 -I 包含路径
---

**编译结束**: 2026-06-17 23:03
**最终状态**: published
