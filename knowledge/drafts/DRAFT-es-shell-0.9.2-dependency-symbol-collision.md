# es-shell 0.9.2：自有全局符号与链接库符号重名（getstr 与 ncursesw）→ duplicate symbol

> 草稿（DRAFT）— 来自 es-shell 0.9.2 HarmonyOS PC (aarch64) 第一轮适配的真实日志。
> 与 `.kv` 同 stem 配对，字段见 knowledge/drafts/DRAFT-es-shell-0.9.2-dependency-symbol-collision.kv

## 问题

es-shell 链接阶段报错：

```
ld.lld: error: duplicate symbol: getstr
>>> defined at lib_gen.c lib_gen.o:(getstr) in archive .../libncursesw.a
>>> defined at term.c term.o:(.text+0x21C)
```

`es` 与 `esdump` 两个二进制都无法生成（Makefile `es:` / `esdump:` 均失败）。

## 根因

es-shell 自带全局函数 `char *getstr(Term *term)`（term.c 定义、es.h 声明、
15 个 .c 文件调用）。同时 configure 检测到 readline 后链接
`-lreadline -lncursesw`；readline 依赖 terminfo 函数（tgetent/tputs/tgetstr
等），导致 libncursesw.a 的 **lib_gen.o**（生成汇总对象）被整体拉入链接，
而 lib_gen.o 恰好包含 curses 的 `int getstr(char*)` → 两个同名全局符号冲突。

这是"自有符号 vs 依赖库符号"冲突，与 E163（OHOS 内核头文件把 `__packed`
定义成全局变量）根因不同：本场景无头文件污染，是链接期符号级撞名。

## 解决方案

把 es-shell 自有 `getstr` 改名 `es_getstr`（机械改名，语义不变）：

```bash
grep -rl '\bgetstr\b' *.c *.h | xargs sed -i 's/\bgetstr\b/es_getstr/g'
```

- 15 个 .c + es.h 共 69 处替换；
- 不触碰 ncurses 的 getstr（程序从不调用 curses 输入函数）；
- 改名后 `es` / `esdump` 链接通过，trip 回归通过。

## 验证

```bash
make   # 链接通过
nm es | grep -w getstr        # 只剩 curses/libncursesw 的（es 侧已改名）
make test                     # trip 通过
```

## 适用边界

- 链接 readline→ncurses(w) 且自带与 curses/terminfo 同名函数的程序；
- 一般化：任何自有全局符号与依赖库（归档/共享库）符号冲突的软件；
- 若能用 `-ltinfo` 等符号子集替代完整 ncurses 链接，也可不改名。

## 反例 / 限制

- 禁止 `--allow-multiple-definition` 掩盖（两个 getstr 语义不同，取先定义者
  不可靠，且属审计失真）；
- 禁止用头文件 `#define` hack（R8）；
- 若冲突符号语义恰好相同（如都是同一函数的重复定义），应先消除重复定义
  而非改名。