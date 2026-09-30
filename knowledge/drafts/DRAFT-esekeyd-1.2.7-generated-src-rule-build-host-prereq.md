# Draft: autotools 生成源文件规则依赖构建机绝对路径且时间戳敏感（esekeyd parser.c）——tarball 已含预生成结果时直接移除规则；自定义规则 VPATH 需 $<

> Source event: `esekeyd/1.2.7` 首次适配（2026-09-29，本机 OHOS clang 交叉编译验证通过；真机 shadow CI 见 notes.md）。
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## 问题

esekeyd 的 `src/Makefile.am` 把**生成源文件** parser.c 声明为普通规则的产物：

```make
noinst_PROGRAMS = mkparser
parser.c: mkparser /usr/include/linux/input.h
	./mkparser /usr/include/linux/input.h > parser.c
```

两个可移植性缺陷：

1. **前提是构建机绝对路径** `/usr/include/linux/input.h`。构建机（容器/交叉环境/
   OHOS 真机）没有该文件时，GNU make 直接
   `No rule to make target '/usr/include/linux/input.h', needed by 'parser.c'`。
2. **时间戳敏感**：tarball 内 parser.c 的 mtime 是 2010 年发布时间，而任何
   现代内核头文件都比它新 → make **每次**都判定需要重建，尝试运行 host 工具
   mkparser；交叉编译时 mkparser 由 `CC_FOR_BUILD`（configure 在 cross 时探测
   `gcc`/`cc`，OHOS 无 gcc）构建/执行都会失败。

而发布 tarball 本来就**自带预生成的 parser.c**（键码→键名映射表，内容只依赖
2010 年代内核 UAPI，稳定），重建既不必要也不可行。

## 根因

上游把"生成器 + 内核头"当作 parser.c 的常规前提，隐含假设「构建机 = 装了
内核头的 Linux 发行版且时间戳天然晚于发布包」。该假设在三类环境全部失效：
交叉编译（CC_FOR_BUILD 不可用）、容器（无 /usr/include/linux）、以及
「tarball 已含生成结果」这一事实本身（时间戳永远输给系统头文件）。

## 修复（补丁，非配方技巧）

规则本身就是错误依赖，直接从 `Makefile.am` 与**预生成的** `Makefile.in`
两处删除（只删 .am 不删 .in 无效——构建用的是 configure 读的 Makefile.in）：

```diff
-parser.c: mkparser /usr/include/linux/input.h
-	./mkparser /usr/include/linux/input.h > parser.c
```

注意保留 `clean-local: rm -f parser.c` 会导致 `make clean` 后无法原地重建
（上游本就要求内核头才可重建）；CI 流程不 clean，不受影响，如需二次构建
须重新解包。

## 同族陷阱②：自定义规则用 $(SOURCES) 破坏 VPATH

同文件的自定义 mkparser 规则：

```make
mkparser: $(mkparser_SOURCES)
	$(CC_FOR_BUILD) -o $@ $(mkparser_SOURCES)
```

out-of-source（VPATH）构建下 make 会在 srcdir 找到 mkparser.c，但
`$(mkparser_SOURCES)` 展开为裸文件名，**编译器不解析 VPATH** →
`no such file or directory: 'mkparser.c'`。只有 GNU make 自动变量
（`$<`、`$^`）才会被 VPATH 重写为解析后的路径：

```diff
-	$(CC_FOR_BUILD) -o $@ $(mkparser_SOURCES)
+	$(CC_FOR_BUILD) -o $@ $<
```

automake 自身生成的 `.c.o` 规则用 `$<`，所以只有**手写自定义规则**会踩；
Conan Autotools/AutotoolsToolchain 默认 out-of-source，命中概率高。

## 验证（esekeyd/1.2.7）

```text
# 本机（Windows + OHOS SDK）：
#   补丁 git apply --check 通过；干净解压实际 apply 后 Makefile.am/.in
#   两处修改生效；6 个 .c 用 --target=aarch64-linux-ohos 全部编译通过，
#   3 个程序链接 AArch64 ELF、NEEDED 仅 libc.so。
# 真机：见 archives/e/esekeyd/1.2.7/notes.md W5 记录。
```

## 禁忌

- 不删 mkparser 的**构建**本身（noinst 工具随主构建编译，是 mkparser.c 可编译性
  的免费回归验证），只删「parser.c 重建规则」与「$(SOURCES) 作编译输入」；
- 不在配方里 `touch parser.c` 糊时间戳（脆弱：依赖解包顺序与系统头 mtime，
  且 Makefile.in 中的绝对路径前提仍会让 make 报 No rule to make target）；
- 改 .am 必须同步改预生成 .in（该包不跑 automake，缺 automake 时 Makefile.in
  才是实际输入；E041/E069 时间戳陷阱正是避免触发 automake 再生）。

## 关系

- complement: E041/E069（automake 再生陷阱，本条以"同步改 .in"规避）、
  E037/E049（构建脚本绝对路径假设同族）、E392（raw makefile 配方要素）
- similar_to: DRAFT-riemann-c-client-1.10.4-pre-generated-sources（同库预生成
  源码 + Makefile.am 改造路线，对象是 protobuf 生成物）

## 查重声明

知识库检索「parser.c 生成规则 / 构建机绝对路径前提 / VPATH $(SOURCES)」无
专门条目；riemann-c-client 草稿针对"缺生成器工具改用预生成源"，本条针对
"规则前提不可移植 + VPATH 自动变量"，根因与解法不同，互补不重复。
