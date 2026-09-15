# 路径 B 知识库扩展申请：生成产物随包时不要触发 bison/flex（直编绕开再生成规则）

## 申请信息

- **申请类型**：路径 B（知识库扩展，10 分候选）
- **关联任务**：#6953 cvs-fast-export 1.59
- **关联 PR**：`!9410`（`feat/cvs-fast-export-1.59`，配方 PR）
- **知识草稿**：`knowledge/drafts/cvs-fast-export-1.59-generated-parser-sources-vs-regen-rules.kv` / `.md`
- **草稿 ID**：`DRAFT-CFE-GENERATED-PARSER-SOURCES-VS-REGEN-RULES`
- **提交方式**：草稿与配方归档**同一原子 PR 分支**（`feat/cvs-fast-export-1.59`）提交
- **申请日期**：2026-09-10

## 一、为什么这是"可跨仓库复用的知识"

本仓库大量包的上游 tarball 里**同时**打包了词法/语法分析器的**生成产物**与**生成源**，
并在 Makefile 里保留再生成规则。`make` 按时间戳判定是否重建，于是构建可能在
"与本包源码毫无关系"的一步因缺 `bison`/`flex` 而失败（CI 镜像不装这两个开发机工具）。
本条给出**一行判据**（`ls *.y *.l` + 同名 `.c` 是否同时存在）、**反向陷阱的区分方法**
（只有 `.y/.l` 无生成物时必须声明 tool_requires）与**三步处置**，可直接套用。

## 二、实例：cvs-fast-export 1.59

**问题**：tarball 同时含

```
gram.c  gram.h   ← 生成产物      gram.y  ← 生成源
lex.c   lex.h    ← 生成产物      lex.l   ← 生成源
```

而 Makefile 保留再生成规则：

```make
gram.h gram.c: gram.y
	$(BISON) $(YFLAGS) --defines=gram.h --output-file=gram.c $(srcdir)/gram.y
lex.h lex.c: lex.l
	$(FLEX) $(LFLAGS) --header-file=lex.h --outfile=lex.c $(srcdir)/lex.l
```

`.y/.l` 时间戳一旦更新（解包顺序、FS 时间精度、`touch`）→ `make` 调用
`bison`/`flex` → **CI 无此工具** → `bison: not found` /
`No rule to make target 'gram.c'`。

**判据（一行）**：

```bash
ls *.y *.l 2>/dev/null && ls -la gram.c lex.c 2>/dev/null
```

**反向陷阱**：若 tarball **只有** `.y/.l` 而无生成物 → bison/flex 是**真依赖**，
必须 `tool_requires` 声明，**不能**靠直编绕过。本条只适用于"生成物随包"。

## 三、处置

1. 判据命中 → 生成物随包型，**直编随包的 `.c`**，不跑 make；
2. 顺带绕开上游混合 make 方言（该 Makefile 同时用 BSD 的 `.PATH`/`.PARSEDIR`/`?=`
   与 GNU 的 `$(shell …)`/`VPATH`）；
3. 在 `notes.md` 写明"使用随包生成物、不触发 bison/flex"及理由，供审计。

## 四、本包顺带处理的两处同源落差

| 落差 | 症状 | 处置 |
|---|---|---|
| `CPPFLAGS += -DVERSION=\"$(VERSION)\"`，`VERSION` 由 `sed` 从 `NEWS.adoc` 抽取；`main.c` 里 `"version " VERSION` 做字面量拼接 | 宏未定义 → **语法错误** | 生成内联头文件 `#define VERSION "1.59"` + `-include` 注入（避开跨 shell 引号转义） |
| `CFLAGS += -pthread` / `CPPFLAGS += -DTHREADS`（上游默认开多线程 collate） | 不开启则行为与上游不一致 | 配方同样传 `-pthread -DTHREADS` |

## 五、验证证据

| 项 | 证据 |
|---|---|
| 构建 | 本地 `conan create archives/c/cvs-fast-export/1.59` **退出码 0**，`Package created` |
| 未引入 bison/flex | 构建命令中不含 `make`，直接用随包的 `gram.c`/`lex.c`；本机亦未安装 bison/flex |
| 产物 | `cvs-fast-export` = ELF64/AArch64，NEEDED 仅 libc.so |
| 消费者测试 | 9 条断言（二进制存在/可执行/架构；`-V` 与 `-h` 真实执行且输出含源码字面；3 个 Python 辅助脚本） |
| 测试判据加固 | 按 AI 检视 P2/P3：命令行退出码把 `126/127/>=128` 一并视为"没跑起来"（popen 经 shell 时信号死亡=128+signum）；循环读干管道才 `pclose` |

## 六、查重声明

- **E392**（raw makefile 三陷阱）：不涉及生成产物与 bison/flex。
- 与同批 **dds2tar** 的「Makefile 宏与 OBJ 契约核对」互补而非重复：那条讲
  "**遗漏** Makefile 注入物"（字符串宏 / 宿主机内核头 / 跨续行 OBJ），本条讲
  "Makefile 里**存在但不该执行**的再生成规则"，判据（`ls *.y *.l`）与处置
  （直编随包生成物）均不同。
- 正式库以 `bison: not found` / `gram.y` / `generated sources` 检索无相关条目。

## 七、请评审确认

1. 是否认可本条目为**路径 B（贡献创新，10 分候选）**评审对象？
2. 是否建议把"生成产物随包 → 直编、不触发 bison/flex；仅源无产物 → tool_requires"
   这条判据写入 `docs/ADAPTATION_GUIDE.md` 的 raw-makefile 章节？
