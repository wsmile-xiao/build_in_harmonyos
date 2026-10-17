# 生成产物随包时不要触发 bison/flex：直编即可（附混合 make 方言与版本宏）

> Draft: `DRAFT-CFE-GENERATED-PARSER-SOURCES-VS-REGEN-RULES`
> Stem: `cvs-fast-export-1.59-generated-parser-sources-vs-regen-rules` — 与同 stem 的 `.kv` 成对
> 实例：cvs-fast-export 1.59（PR !9410）

## 基本信息

- **ID**: DRAFT-CFE-GENERATED-PARSER-SOURCES-VS-REGEN-RULES
- **严重度**: 2
- **类别**: conan, makefile, build-deps, generated-sources
- **触发工具**: make / ci
- **阶段**: build

## 问题

cvs-fast-export 的 tarball **同时**包含：

```
gram.c  gram.h    ← 由 gram.y 生成的产物
lex.c   lex.h     ← 由 lex.l 生成的产物
gram.y  lex.l     ← 生成源
```

而 Makefile 保留了再生成规则：

```make
gram.h gram.c: gram.y
	$(BISON) $(YFLAGS) --defines=gram.h --output-file=gram.c $(srcdir)/gram.y
lex.h lex.c: lex.l
	$(FLEX) $(LFLAGS) --header-file=lex.h --outfile=lex.c $(srcdir)/lex.l
```

`make` 按**时间戳**决定是否重建。只要 `.y`/`.l` 比 `.c` 新（解包顺序、文件系统
时间精度、`touch` 都能造成），`make` 就去调 `bison`/`flex` —— 而 **CI 镜像不装
这两个工具**（它们是开发机工具，不是运行时依赖）。构建于是在与本包源码毫无关系的
一步失败：

```
bison: not found            （或）
No rule to make target 'gram.c'
```

## 一行判据

```bash
ls *.y *.l 2>/dev/null && ls -la gram.c lex.c 2>/dev/null
grep -nE '^(\S+)\.(c|h):.*\.(y|l)' Makefile
```

**同时命中** = 生成物随包，直编即可。

## 反向陷阱（必须区分）

若 tarball **只有** `.y`/`.l` 而**没有**生成物 → bison/flex 是**真依赖**，
必须显式声明构建依赖（`tool_requires`），**不能**靠直编绕过。本条只适用于
"生成物同时也打进包里"的情形。

## 处置（三步）

1. **判定**：`ls *.y *.l` 有命中且同名 `.c` 也在包里 → 生成物随包型；
2. **直编**：把 `gram.o`/`lex.o` 照样编译**随包的 `.c`**，不跑 make。顺带绕开上游
   一堆 make 方言问题（见下）；
3. **留证**：在 `notes.md` 写明"使用随包生成物、不触发 bison/flex"及理由。

附带检查：`gram.c` 与 `gram.h` 必须来自**同一次**生成（通常同时打包），
否则会因原型不一致报编译错误。

## 本包顺带绕开的另外两处（同源：直编 vs Makefile 契约）

### 混合 make 方言

该 Makefile **同时**使用 BSD make 与 GNU make 语法：

```make
.PATH: $(.PARSEDIR)        # BSD make
prefix?=/usr/local         # BSD/GNU 都有
VERSION=$(shell sed -n <NEWS.adoc …)   # GNU make
VPATH=$(srcdir)
```

直编可绕开全部方言差异。

### 版本宏是「从文档抽取 + 字符串字面量注入」

```make
VERSION=$(shell sed -n <NEWS.adoc '/::/s/^\([0-9][^:]*\).*/\1/p' | head -1)
CPPFLAGS += -DVERSION=\"$(VERSION)\"
```

而 `main.c: printf("%s: version " VERSION "\n", argv[0]);` —— 宏未定义即**语法错误**。
配方改为**生成内联头文件 + `-include`** 注入 `#define VERSION "1.59"`
（取值从 `NEWS.adoc` 首个含 `::` 的行读出），既复刻宏又避开 cmd.exe/POSIX sh
的引号差异。

### 多线程开关

```make
CFLAGS += -pthread
CPPFLAGS += -DTHREADS
```

上游默认开启（collate 并行），配方同样开启，保证行为一致。

## 边界与查重

- **E392**（raw makefile 三陷阱：BadZipFile / compiler_executables / make cwd）：
  不涉及生成产物与 bison/flex。
- 本条与同批的 **dds2tar**「Makefile 宏与 OBJ 契约核对」互补：那条讲"遗漏 Makefile
  注入物"，本条讲"Makefile 里**存在但不应执行**的再生成规则"，判据与处置均不同。
- 正式库以 `bison: not found` / `gram.y` / `generated sources` 检索无相关条目。

## 关联

- 配方 PR：**!9410**（cvs-fast-export 1.59 适配 HarmonyOS PC，分支 `feat/cvs-fast-export-1.59`）
- 平台任务：#6953（cvs-fast-export 1.59）
- 本 Issue 与 PR 双向关联；草稿经主编审核后由 promote 流程转入正式知识库。
