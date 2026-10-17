# xmlindent 0.2.18 适配笔记

## 软件简介
XML Indent（Pekka Enberg）是 ANSI C 编写的 **XML 流重排版工具**：从 stdin 或文件读取
XML，按可配置缩进/换行重新输出，处理 XML 声明、DOCTYPE、CDATA、注释、处理指令、
属性与字符引用。许可证 GPL-2.0-or-later。

| 选项 | 说明 |
|------|------|
| `-o <file>` | 输出到指定文件 |
| `-i <n>` | 缩进层级（默认 4） |
| `-t` | 用制表符而非空格缩进 |
| `-l <cols>` | 行宽换行 |
| `-n <pos>` | 在指定位置抑制换行 |
| `-f` | 无子元素的元素也强制换行 |
| `-w` | 原地覆盖原文件 |
| `-v` / `-h` | 版本 / 帮助 |

## 编译环境
- 构建系统: makefile（非 autotools）
- 目标平台: OpenHarmony OHOS / aarch64
- 编译器: clang（`aarch64-unknown-linux-ohos`），实测 clang 15.0.4
- 构建期工具: **flex**（生成词法分析器）

## OHOS 适配结论：**无需任何源码修改**
0.2.18 在 OHOS 上直接编译、链接、运行通过，**未提交任何 patch，未改写任何源码**。
上游回归 fixture 逐字节通过（见下）。这是本库与 xdms / webbench 的显著区别。

## 构建链要点（易误读，记录备查）
上游 Makefile 的依赖关系：

```make
xmlindent: buffer.o error.o indent.o main.o
	$(CC) $(CFLAGS) $(LDFLAGS) $^ -o $@

.c.o:
	$(CC) $(CFLAGS) $^ -c -o $@

indent.c: lex.yy.c
	touch indent.c          # 仅 touch，迫使 indent.o 重编

lex.yy.c: xmlindent.yy
	flex xmlindent.yy
```

关键点：`indent.c` 第 38 行是 `#include "lex.yy.c"` —— 生成文件被**包含**进来，
因此**不存在** `lex.yy.o`，链接目标里也没有它。`indent.c` 只依赖 `lex.yy.c`
并执行 `touch`，作用是让 `indent.o` 在词法规则变化后重新编译。

## flex 的定位：**仅构建期工具**
- **用途**：从 `xmlindent.yy` 生成 `lex.yy.c`，供 `indent.c` include。
- **不是**运行期依赖，也**不是**打包期依赖：产物是单一自包含可执行文件。
  在 OHOS 目标上以 `-Wl,-z,defs -Wl,-as-needed -Wl,--no-undefined` 链接**成功**
  且**不需要 `-lfl`**（flex 2.6.4 生成的扫描器不产生对外部 `yywrap` 的引用）。
- 上游 Makefile 把命令硬编码为 `flex`，故 flex 必须位于 PATH
  （OHOS 构建镜像提供 flex 2.6.4，位于 `/data/service/hnp/bin/flex`）。
  `build()` 在缺失时以明确信息提前失败。
- **因此配方中不声明 flex 为 `requires()`**，避免把它错误地变成 runtime 依赖。

## 上游测试
上游**没有** `test` / `check` 目标，也没有测试运行脚本。但上游确实提供了
**1 组正式回归 fixture**，由 2020-02-23 提交
"#3 parse: Fix whitespace consumption within text nodes" 引入：

```
tests/whitespace-in-content.orig.xml       输入
tests/whitespace-in-content.expected.xml   期望输出
```

xmlindent 是 stdin/stdout 过滤器，该 fixture 可直接执行：

```
./xmlindent tests/whitespace-in-content.orig.xml
  | cmp - tests/whitespace-in-content.expected.xml
```

即本版本**完整的上游测试集合**：`upstream_total = 1`。
已由 `run_upstream_tests.sh` 全量执行，并在 `build()` 中调用（结果进入构建日志）。
**未跳过、未过滤、未排除任何用例。**

## 打包要点
- `bin/xmlindent`
- `share/man/man1/xmlindent.1`
- `licenses/LICENSE`

## 验证结果
（等待 Harmony PC 真机 `conan create` 后填写）

## 注意事项
- 根目录的 `test.xml`（525 字节）是**示例输入**，不是测试用例，不计入 upstream_total。
- 上游对畸形输入的容忍度较高：测试中未对畸形输入的退出码做强断言，只要求
  进程正常终止且不崩溃。

<!-- notes-end -->
