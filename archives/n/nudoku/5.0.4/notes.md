# nudoku 5.0.4 适配笔记

## 源码版本说明

上游 nudoku 的 5.x 系列仅有 `5.0.0` 一个发布标签（GitHub `git/matching-refs/tags/5` 仅返回 `5.0.0`；更高版本为 6.0.0 / 7.0.0 / 8.0.0 / 8.0.1，**不存在 5.0.4**）。本配方按任务要求以 `5.0.4` 作为包版本 / 分支 / 路径，源码取 5.x 基线 `5.0.0` 官方 tarball（conandata.yml 指向其官方 URL 与真实 sha256），并以 `-DVERSION="5.0.4"` 注入版本号，`nudoku -v` 输出 `nudoku version 5.0.4`。

## 编译环境

- 构建系统: custom（直接 clang 编译；上游为 autotools）
- 编译日期: 2026-07-14
- 编译器: clang 15.0.4
- 状态: built

## 为何不使用 autotools

上游官方 GitHub 源码包是纯 git 快照，**仅含 configure.ac**，没有预生成的 `configure` / `Makefile.in` / `config.guess`。走 autotools 需要 `autoreconf -i`，而 configure.ac 含 `AM_GNU_GETTEXT([external])`（需 autopoint/gettext）与 `PKG_CHECK_MODULES([ncursesw])`（需 ncursesw.pc），在 OHOS/musl 上有多个脆弱点。nudoku 仅两个翻译单元——`src/main.c`（ncurses UI）与 `src/sudoku.c`（纯 C 求解器，不依赖 ncurses）——故直接用 Conan 提供的 clang 编译，确定性更高，且不引入 gettext/pkg-config 依赖。

## 编译步骤

```bash
cc=$(conan conf tools.build:compiler_executables:c)   # clang
ar=$(conan conf tools.build:compiler_executables:ar)  # llvm-ar
PREFIX=/storage/Users/currentUser/usr/local           # 系统静态 ncurses

CFLAGS="-O2 -DVERSION=\"5.0.4\" -DLOCALEDIR=\"/usr/local/share/locale\" \
        -I$PREFIX/include -I$PREFIX/include/ncursesw"

# 1) 求解器静态库（纯 C，不依赖 ncurses）
$cc $CFLAGS -c src/sudoku.c -o sudoku.o
$ar rcs libnudoku.a sudoku.o

# 2) TUI 二进制：main.c + libnudoku + 系统 libncursesw.a
$cc $CFLAGS -c src/main.c -o main.o
$cc main.o -L. -lnudoku -L$PREFIX/lib -l:libncursesw.a -o nudoku

# 安装
cp nudoku      $PREFIX/bin/
cp libnudoku.a $PREFIX/lib/
cp src/sudoku.h $PREFIX/include/
```

## 产物

| 文件 | 说明 |
|------|------|
| `bin/nudoku` | ncurses 数独游戏（ELF, aarch64, 动态链接 musl libc，静态链接 ncurses） |
| `lib/libnudoku.a` | 求解器静态库（供 test_package 调用 solve / is_valid_puzzle） |
| `include/sudoku.h` | 求解器头文件 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `VERSION` 未定义，编译报错 | VERSION 由 autotools 注入，源码仅留注释 | CFLAGS 加 `-DVERSION=\"5.0.4\"` |
| 2 | ncurses.h/curses.h 在所有 worker 上均找不到（#1841/#1843/#1847） | CI worker 只装 ncurses 运行时库（libncursesw.so，shell 依赖），**无 dev 头文件**：pkg-config 无 ncurses、`$DEFAULT_PREFIX/include`、`/usr/include` 等均无头文件（bitwise 配方亦印证"CI worker has ncurses .a but no headers"） | 打包 ncurses 头文件 + 匹配的静态 libncurses.a 到 `res/`（取自 bitwise 的 `res/`），build() 用 `-I res/headers` + `-L res/libs -lncurses`；main.c 的 `<ncurses.h>` 改 `<curses.h>` |
| 3 | test_package 需"调用库 API" | nudoku 只产二进制，无 linkable 库 | 将 sudoku.c 编为 libnudoku.a 并安装，test_package 链接调用 solve/is_valid_puzzle |
| 4 | gettext.h 内未用 static 函数引用 dcgettext | gnulib gettext.h 的 pgettext_aux 等恒定义 | `-O2` 死代码消除移除未用 static 函数，不产生 libintl 引用 |
| 5 | build() 报 `tools.build:compiler_executables:c does not exist` | 该子 conf 未注册；CI profile 用 dict 形式 `tools.build:compiler_executables={'c':...,'cpp':...}` | 读 dict 取 c 编译器；ar/ranlib 未提供，由编译器同目录推导 `llvm-ar`（参考 fontconfig/cairo） |

## test_package

- `test.c`：调用 `is_valid_puzzle()` / `solve()`——对合法谜题断言 valid 且 `solve≥1`；对非法谜题（首行两个 `1`）断言 invalid 且 `solve==0`。共 4 个断言。
- `conanfile.py`：编译 test.c 链接 libnudoku.a 运行；并以 `nudoku -v` 烟测二进制。

## 依赖

- ncurses（系统预装静态库 libncursesw.a），无 Conan 依赖。

## 验证结果

```bash
$ nudoku -v
nudoku version 5.0.4

Copyright (C) Michael Vetter 2014 - 2024
License GPLv3+: GNU GPL version 3 or later.
...

$ file bin/nudoku
ELF ... arm64, dynamic (/lib/ld-musl-aarch64.so.1)

$ ./test
PASS: nudoku solver test (1 solution(s) for the valid puzzle)
```
