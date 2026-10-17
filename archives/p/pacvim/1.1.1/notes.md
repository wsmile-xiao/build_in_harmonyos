# pacvim 1.1.1 适配笔记

## 编译环境
- 构建系统: makefile（原始为简单Makefile，无configure脚本，非autotools）
- 编译日期: 2026-06-15
- 编译器: clang 15.0.4 / clang++
- 平台: 鸿蒙 (OpenHarmony) aarch64
- 状态: built

## 编译步骤

1. 下载并解压源码：`python3 $SKILL_ROOT/scripts/ohc-run.py init-build pacvim 1.1.1 --url=...`
2. 修改 Makefile：
   - 添加 DESTDIR ?= 支持（install 目标路径加 $(DESTDIR)）
   - CXX 改为 `?= clang++`（允许命令行覆盖）
   - PREFIX 改为 `?= /usr/local`（允许命令行覆盖）
   - 添加 EXTRA_INC ?= 和 EXTRA_LIB ?= 变量，CFLAGS 加 `-I$(EXTRA_INC)`，LFLAGS 加 `-L$(EXTRA_LIB)`
3. 修改 src/globals.h：将 `#ifdef __APPLE__/#include <curses.h>/#else/#include <cursesw.h>/#endif` 替换为统一 `#include <cstddef>/#include <curses.h>`
4. 修改 src/helperFns.h：将 `#ifdef __APPLE__/#include <curses.h>/#else/#include <cursesw.h>/#endif` 替换为统一 `#include <curses.h>`
5. 编译：`make PREFIX=$DEFAULT_PREFIX -j1`
6. DESTDIR安装：`make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX`
7. 本地安装：`make install PREFIX=$DEFAULT_PREFIX`（不带DESTDIR，模拟用户部署）
8. 打包：`python3 $SKILL_ROOT/scripts/ohc-run.py package pacvim 1.1.1`
9. 收尾：`python3 $SKILL_ROOT/scripts/ohc-run.py finish pacvim 1.1.1 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译报错 `'cursesw.h' file not found` | 鸿蒙平台 ncurses 仅提供 curses.h，无 wide-char 版本 cursesw.h | 将 globals.h 和 helperFns.h 中的条件编译 `#ifdef __APPLE__...#else #include <cursesw.h>` 替换为统一 `#include <curses.h>` |
| 2 | 编译报错 `'curses.h' file not found` | clang++ 默认搜索路径不包含 ~/usr/local/include（ncurses头文件位置） | 在 Makefile 中添加 EXTRA_INC/EXTRA_LIB 变量，CFLAGS 加 `-I$(EXTRA_INC)` |
| 3 | Makefile 不支持 DESTDIR | 原始 Makefile install 目标缺少 DESTDIR，无法做 staging 隔离 | 添加 `DESTDIR ?=` 变量，install 目标路径改为 `$(DESTDIR)$(BINDIR)` 等 |
| 4 | Makefile CXX/PREFIX 硬编码 | 原始 Makefile CXX=g++、PREFIX=/usr/local，不允许命令行覆盖 | 改为 `?= clang++` 和 `?= /usr/local` |

## 源码修改

- **Makefile**: 添加 DESTDIR 支持、CXX/PREFIX 改为可覆盖(?=)、添加 EXTRA_INC/EXTRA_LIB、install 目标路径加 $(DESTDIR)
- **src/globals.h**: 去掉 `#ifdef __APPLE__` 条件分支，统一使用 `#include <cstddef>` + `#include <curses.h>`
- **src/helperFns.h**: 去掉 `#ifdef __APPLE__` 条件分支，统一使用 `#include <curses.h>`

## 依赖版本

- ncurses（静态库 libncurses.a，通过预编译包安装于 ~/usr/local）

## 验证结果

```bash
# 二进制类型
$ file /storage/Users/currentUser/usr/local/bin/pacvim
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

# ELF头信息
$ readelf -h /storage/Users/currentUser/usr/local/bin/pacvim
Machine: AArch64, Type: DYN (Position-Independent Executable)

# 动态库依赖
$ readelf -d /storage/Users/currentUser/usr/local/bin/pacvim | grep NEEDED
  NEEDED: libc++_shared.so
  NEEDED: libc.so

# 功能验证 - 帮助信息
$ /storage/Users/currentUser/usr/local/bin/pacvim --help
Invalid arguments. Try ./pacvim or ./pacvim #
EG: ./pacvim 8

# 功能验证 - 游戏启动（timeout 3秒后正常退出，界面渲染正常）
$ timeout 3 /storage/Users/currentUser/usr/local/bin/pacvim
LEVEL 0 ... PRESS ENTER TO PLAY! ... ESC OR q TO EXIT!
（游戏界面正常渲染，ncurses功能验证通过）

# 地图文件完整性
$ ls /storage/Users/currentUser/usr/local/share/pacvim-maps/
map0.txt ~ map9.txt（10个文件完整）

# 预编译包解压验证
$ tar tzf pacvim-1.1.1-ohos-aarch64.tar.gz
bin/pacvim, share/pacvim-maps/map0~9.txt（11个文件）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pacvim-1.1.1-ohos-aarch64.tar.gz | 547KB | 预编译包（含bin/pacvim + 10个地图文件） |
| pacvim-1.1.1-ohos-aarch64-debug.tar.gz | 237KB | 调试符号包 |
| 0001-Makefile.patch | +10/-7 | Makefile平台适配补丁 |
| 0002-src-globals.h.patch | +1/-5 | globals.h头文件替换补丁 |
| 0003-src-helperFns.h.patch | +1/-5 | helperFns.h头文件替换补丁 |

## 注意事项

- PacVim 是交互式 ncurses 游戏程序，需要终端环境运行，无 --version 输出
- 项目实际为纯 Makefile 构建（无 configure 脚本），虽任务标注为 autotools，实际按 makefile 方式处理
- 编译有 format-security 警告（3处 printw/mvprintw 参数），不影响功能
- 依赖 ncurses 需通过预编译包安装，否则编译找不到头文件和库
---

**编译结束**: 2026-07-21 11:55
**最终状态**: built
