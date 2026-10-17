# 上游把 `errno` 当局部变量名声明：一种 libc 编不过、另一种编过但错误检查成死代码

> 路径 B 知识条目（随 proda 1.0 的 PR 原子提交）。
> 来源：通用池草稿 `DRAFT-PKG-VER-libc-errno-name-used-as-local-variable`，本包为**首个实证先例**，
> 复制改名后把证据字段换成 proda 1.0 的实测值。
> 本 PR 的另一机制（plain `char` 承接 `fgetc()` 再比 `EOF`）判为 **hit** 既有库
> （`knowledge/drafts/E547-draft-B5C3.kv`、`DRAFT-8543-plain-char-eof-sentinel-infinite-loop.kv`），
> 按"一 PR 一知识"**不**在本条主张。

## 一句话机制

`errno` 在 **glibc 和 musl 上都是宏**（`(*__errno_location())`），不是对象。上游若写

```c
int errno = 0;                    // ← 把保留名当普通局部变量声明
retVal = strtol(data, &endPtr, 0);
if (retVal == 0 && (errno != 0 || data == endPtr)) return false;
```

那么**这行能不能编译，只取决于该翻译单元里 `errno` 宏有没有被某条 include 链带进来**：

| 臂 | `errno` 宏是否已进入 | 结果 |
|---|---|---|
| A | **未进入**（glibc 的常见构建链） | **编译通过**，但此后所有 `errno != 0` 读的都是这个局部 int，而 `strtol` 写的是**真线程 errno** ⇒ 错误检查**恒为假 = 死代码**，非法输入被静默接受 |
| B | **已进入**（musl 若干公共头会间接拉入 `errno.h`） | 声明先被展开成 `int (*__errno_location()) = 0;` ⇒ clang 报 **`error: illegal initializer`**，症状完全看不出根因是"变量名撞宏" |

⇒ **同一段上游代码在两种 libc 上表现相反：要么编不过，要么静默失效。**
后者更危险——它在 CI 上是绿的，只在真实输入触到边界时才暴露。

## 本包实测落点

- 文件与行号：`Main.cc:119`，解析辅助函数 `GetInteger()` 内的 `int errno = 0;`。
  该翻译单元原本**不** `#include <errno.h>`。
- 报错原文（B 机，clang 15，target `aarch64-unknown-linux-ohos`）：
  `Main.cc:119:7: error: illegal initializer (only variables can be initialized)`，
  紧跟一行 note 指向 `errno.h:16:17: expanded from macro 'errno'` —— 根因与症状相距很远。
- 受影响调用点：全仓 grep 后确认 `GetInteger()` 的**唯一**调用点是命令行 `-L <length>` 的取值解析。
- 行为中性论证（本包实测，不是推演）：
  ① 非数字输入 → 改前改后都由 `retVal == 0 && data == endPtr` 这条拦住 ⇒ `return false`；
  ② 溢出输入 → `strtol` 返回 `LONG_MAX`/`LONG_MIN`，改前落到 `retVal < INT_MIN || retVal > INT_MAX`
  也照样 `return false`。两条路径结论相同 ⇒ **修掉遮蔽 bug 的同时不改变任何可观测行为**，
  因此不新增"非法输入改判"的披露项（消费者测试 A25/A26 已覆盖 `-L abc` 的退出码与诊断文本）。
- 补丁：`archives/p/proda/1.0/patches/0001-Main.cc-name-shadowed-libc-errno.patch`
  （include 段加 `<errno.h>`；`int errno = 0;` → `errno = 0;`，即去掉类型名使其成为对宏的赋值）。
  新增行**不含任何平台宏**。

## 归因纪律：这是上游缺陷被 OHOS 揭出来，不是 OHOS 不兼容

看到 `illegal initializer` 就写"musl 不支持 errno"是**方向性错误**：两边都有 `errno`，
只是 OHOS 用的 musl 头链把宏带进来了，于是上游的命名违规**从潜伏变成显性**。
proda 这一例修完之后，musl 与 glibc 上的行为**都变正确**（glibc 侧原先是死代码）。

## 最小复现（两臂对照，别只跑一臂）

```sh
# A 臂：不 include errno.h —— 预期编过，但错误分支永不触发
printf '#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\nint main(void){const char*d="abc";char*e;int errno=0;long r=strtol(d,&e,0);if(errno!=0){puts("ERR");return 1;}printf("SILENT-OK %ld\\n",r);return 0;}\n' > arm_a.c
# B 臂：显式 include errno.h —— 预期 clang 直接 illegal initializer
printf '#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n#include <errno.h>\nint main(void){const char*d="abc";char*e;int errno=0;long r=strtol(d,&e,0);if(errno!=0){puts("ERR");return 1;}printf("SILENT-OK %ld\\n",r);return 0;}\n' > arm_b.c
clang -t aarch64-unknown-linux-ohos -c arm_a.c -o a.o   # rc=0，跑起来打印 SILENT-OK（非法输入被接受）
clang -t aarch64-unknown-linux-ohos -c arm_b.c -o b.o   # error: illegal initializer
```

⚠ 两臂都要跑：只跑 B 臂会把它当成"编译问题"，看不出 A 臂的**静默死代码**才是这条知识更值钱的一半。

## 最终方案（推荐）

删掉局部声明 + **显式** `#include <errno.h>`，让原语句变成对宏的正确赋值：

```diff
 #include <stdio.h>
+#include <errno.h>
 #include <stdlib.h>
@@
-  int errno = 0;
+  errno = 0;
```

- 编译期的宏冲突消失；
- `strtol` 的错误检查**从死代码恢复生效**。

⚠ **一般情形下这是一条行为变化，不是纯编译修复**：修复后，原本被静默接受的非法输入会被拒绝。
必须在 notes 与 PR 正文写明这一点，并纳入测试断言。
⚠ proda 这一例经逐路径论证 + 实测**行为中性**（见上节，两条非法路径改前改后都由别的判定拦住）
⇒ "**是否**构成行为变化要看该调用点的实际判定链，不许照抄本条的默认结论"。

⛔ **禁止用改名绕过**（例如把局部变量改成 `err_no`）：那样保留了"错误检查读的不是真 errno"的死代码本质。

## 备选方案（上游确有自己的一套错误码语义时）

若核实上游那个 `errno` **本来就是自用的局部错误码**、与 libc 无关，则：改名 **并且** 把判定改成
真读 `errno`（或改为直接检查 `strtol` 返回值 + `endPtr`）。
判据是先 `grep` 出该变量的所有读写点逐点定语义——**不许**猜。proda 的读写点只有 3 处，全部在
`GetInteger()` 内，且语义就是"libc errno"，故走推荐方案。
⚠ 走这条路必须让错误检查**真的生效**，否则等于把静默缺陷固化下来。

## 适用边界（请勿越界申报）

- 成立：`int errno`/`errno` 被当标识符声明的这一类上游写法。
- **不成**立：`"OHOS 没有 errno"`、`"musl 与 glibc 的 errno 语义不同"`、
  `"errno 不是线程局部"`（三者本条都未验证且方向相反）。
- 与线程局部性、`signal` 族、V8 运行期 `Check failed ... __errno_location`（E400）都是**不同层次**的事。
- 与 `E534`（musl 缺 GNU/BSD 扩展函数 = **符号缺失**）也不同：本条两侧 libc **都有** `errno`，
  缺的是上游写法的正确性。

## 知识库查重（本包按双向口径重做过）

⚠ **查重面必须同时覆盖 `knowledge/graph/` 与 `knowledge/drafts/`** —— 本包初判只扫了
`knowledge/graph/index.tsv` 就写下"全量检索零命中"，被 W4 独立审计判为不实陈述（机制③其实在
drafts 层已有两条）。修正后的检索结果：

- `knowledge/graph/` 命中 `errno` 关键词的 4 行分别是 E008 / E190 / E405 / E415：
  逐条读原文后**没有一条**讲"上游把 errno 当变量名声明"（E190 是 Perl XS `Makefile.PL` 参数，
  `engine` 检索给 0 分，属假命中）。
- `knowledge/graph/` 对 `illegal initializer`、`__errno_location`：唯一实质候选 `E400.kv` ——
  **读原文判为假阳性**：其 `title` 是
  "Node.js CLI on HarmonyOS: JITless/WASM capability boundary and cross-UID package-cache consumer validation"，
  `error_signature` 里的 `Check failed.*__errno_location` 是 **V8 运行时断言**场景，
  与本条"C 源码级命名撞宏 / 编译期-静默双态"不同层次、不同解法。
- `knowledge/drafts/` 定向检索「局部变量 × errno 宏 × illegal initializer」：**0 命中**。

⇒ 判 `create`。**新增价值**：给出"**一个上游缺陷在两种 libc 上以相反形态暴露**"的判别范式，
以及"修它通常属于**行为变化**（可接受输入集改变），必须逐调用点论证后披露"这条容易被漏掉的交付要求。
⚠ 提醒复核者：**grep 命中 ≠ 语义命中**，判 hit 前必须把候选条目的 `root_cause`/`affected_scope` 读完；
反过来"某一处没命中"也 ≠ 库里没有。
