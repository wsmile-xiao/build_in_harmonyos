# DRAFT-14410 — 静态系统同名库（ncurses）与目标程序同名符号冲突（beep）

## 错误特征

```
$ make CC=<clang> LIBS='-L<ncurses>/lib -lncursesw' LDFLAGS='-Wl,--allow-multiple-definition' utalk
ld.lld: error: duplicate symbol: beep
>>> defined at termcap.c:141 (termcap.c:141)
>>>            termcap.o:(beep)
>>> defined at lib_beep.c
>>>            lib_beep.o:(.text+0xAC) in archive <ncurses>/lib/libncursesw.a
clang-15: error: linker command failed with exit code 1
```

## 触发条件

- 阶段: 链接（`conan create` / finish W3 的 make 步骤）
- 前置: 目标程序把 **系统同名库**（ncurses）按 **R26 静态链接**（`libncursesw.a`）
- 目标程序自身定义了 ncurses 也提供的同名函数（本例 `beep`）

## 根因分析

1. R26 要求系统同名库静态链接，避免运行期劫持系统 `libncursesw.so`。
2. 静态链接会把 `libncursesw.a` 中被引用到的归档成员（`lib_beep.o`）整体纳入符号表。
3. utalk 自带 `termcap.c:140 void beep(void)`（其 `termcap.h:36` 声明），与 ncurses 的 `beep` 强定义冲突 → `ld.lld` 直接报错。
4. 在 Linux 上因 ncurses 是共享库，可执行文件可覆盖共享库符号，故上游从不报错——**该问题只在 OHOS 的静态链接组合下暴露**。

## 验证

```
$ llvm-nm <ncurses>/lib/libncursesw.a | grep -w beep
00000000000000ac T beep
```

## 修复

链接参数加 `-Wl,--allow-multiple-definition`（目标文件定义优先，符合上游意图）：

```
LDFLAGS='-Wl,--allow-multiple-definition'
```

仓库先例：`archives/c/cflow`、`archives/d/dovecot`、`archives/e/ettercap`、`archives/f/freeimage`。

## 兜底

若同名符号语义确实不同（不是“覆盖”关系），应改写目标程序侧符号名（`beep` → `utk_beep`）并同步头文件与全部调用点。
