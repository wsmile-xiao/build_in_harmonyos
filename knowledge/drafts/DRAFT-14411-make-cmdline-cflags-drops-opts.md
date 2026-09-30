# DRAFT-14411 — 命令行覆盖 CFLAGS 丢弃手写 Makefile 的 OPTS 宏定义

## 错误特征

```
$ make CC=<clang> CFLAGS="-O2 -g -Wall -D__USE_FIXED_PROTOTYPES__" LIBS='-L<ncurses>/lib -lncursesw' utalk
menu.c:677:44: error: use of undeclared identifier 'LIBDIR'
  sprintf(help_txt[1], "help file %s %s.", HELPFILE, s);
./menu.h:20:18: note: expanded from macro 'HELPFILE'
#define HELPFILE LIBDIR "/utalk.help"
make: *** [<builtin>: menu.o] Error 1
```

## 触发条件

- 阶段: 编译（手写 Makefile 项目）
- 前置: 配方/脚本用 **命令行 make 变量 `CFLAGS=…`** 覆盖编译标志
- Makefile 把编入源码的宏放在被同一条 CFLAGS 展开的 `OPTS` 变量里

## 根因分析

utalk 的 `Makefile`：

```make
OPT5 = -DLIBDIR="\"$(LIBDIR)\""
OPTS = $(OPT1) $(OPT2) $(OPT3) $(OPT4) $(OPT5)
CFLAGS = -O2 -g -Wall -D__USE_FIXED_PROTOTYPES__ $(OPTS)
```

make 的**命令行变量优先级最高**：`make CFLAGS=...` 会整体替换 Makefile 中的 `CFLAGS` 赋值（不是追加），于是 `$(OPTS)`（含 `-DLIBDIR`）全部丢失，`menu.c` 的 `HELPFILE` 宏无法展开。

注意：`make: *** [<builtin>: menu.o]` 中的 `<builtin>` 是 make 的**内建隐式规则**——该 Makefile 未显式写 `.c → .o` 规则，属正常现象，不代表工作目录错误。

## 验证

```
$ make -n CC=<clang> CFLAGS='-O2' utalk | grep -c -- '-DLIBDIR'
0
$ make -n CC=<clang> utalk | grep -c -- '-DLIBDIR'
2        # 不覆盖 CFLAGS 时，OPTS 中的 -DLIBDIR 正常出现
```

## 修复

只覆盖必需变量（`CC` / `LIBS` / `LDFLAGS`），**不覆盖 `CFLAGS`**：

```
make -j1 CC=<clang> LIBS='-L<ncurses>/lib -lncursesw' \
     LDFLAGS='-Wl,--allow-multiple-definition' utalk
```

## 兜底

在 Makefile 增加 `CFLAGS += $(EXTRA_CFLAGS)` 之类的追加型入口，用 `EXTRA_CFLAGS` 注入标志，避免整体替换语义。
