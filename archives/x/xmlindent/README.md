# xmlindent — OpenHarmony 编译档案

## 软件简介
XML Indent（Pekka Enberg）是 ANSI C 编写的 **XML 流重排版工具**：从标准输入或文件
读取 XML，按可配置的缩进与换行重新输出。支持 XML 声明、DOCTYPE、CDATA 段、注释、
处理指令、属性解析与字符引用。许可证 GPL-2.0-or-later。
本次适配上游发布版 **0.2.18**。

| 选项 | 说明 |
|------|------|
| `-o <file>` | 输出到指定文件 |
| `-i <n>` | 缩进层级，默认 4 |
| `-t` | 使用制表符缩进 |
| `-l <cols>` | 行宽（超过则换行） |
| `-n <pos>` | 在指定位置抑制换行 |
| `-f` | 无子元素的元素亦强制换行 |
| `-w` | 原地覆盖原文件 |
| `-v` / `-h` | 版本 / 帮助 |

## OHOS 适配结论
**无需任何源码修改。** 0.2.18 在 `aarch64-unknown-linux-ohos`（clang 15.0.4）上
直接 `make CC=clang` 即可编译、链接、运行通过，上游回归 fixture 逐字节通过。
本档案**未提交任何 patch**。

- **构建系统**：普通 Makefile（非 autotools）。生成链为
  `xmlindent.yy --flex--> lex.yy.c`，而 `indent.c` 以 `#include "lex.yy.c"`
  引入该生成文件 —— 因此**不存在** `lex.yy.o`，链接目标只有
  `buffer.o error.o indent.o main.o`。`indent.c` 仅被 `touch`，作用是让
  `indent.o` 在词法规则变化后重新编译。
- **链接**：`-Wl,-z,defs -Wl,-as-needed -Wl,--no-undefined`，在 OHOS 上通过。

## flex 的定位（重要）
flex **仅用于构建期**从 `xmlindent.yy` 生成 `lex.yy.c`。

- **不是**运行期依赖，也**不是**打包期依赖 —— 产物是单一自包含可执行文件，
  运行不需要 flex、libfl 或任何其它库。实测在 OHOS 上链接
  `-Wl,--no-undefined` **通过且不需要 `-lfl`**（flex 2.6.4 生成的扫描器
  不产生对外部 `yywrap` 的引用）。
- 上游 Makefile 把生成命令硬编码为 `flex`，故 flex 必须位于 PATH
  （OpenHarmony 构建镜像提供 flex 2.6.4，位于 `/data/service/hnp/bin/flex`）。
- 因此配方中**不**把 flex 声明为 `requires()`，避免错误地变成 runtime 依赖。

## 依赖关系
- 运行期：无第三方库依赖（仅 C 运行时）
- 构建期：flex（生成词法分析器）
- 被依赖: 无（独立 CLI 工具）

## 上游测试
上游**没有** `test` / `check` Makefile 目标，也没有测试运行脚本。但上游提供了
**1 组正式回归 fixture**（2020-02-23 提交
"#3 parse: Fix whitespace consumption within text nodes" 引入，见 ChangeLog）：

```
tests/whitespace-in-content.orig.xml       输入
tests/whitespace-in-content.expected.xml   期望输出
```

xmlindent 是 stdin/stdout 过滤器，该 fixture 可直接执行并逐字节比对，
即本版本**完整的上游测试集合**：`upstream_total = 1`。

本档案通过 `run_upstream_tests.sh` **全量执行**该用例（在 `build()` 中调用，
结果进入构建日志），**未跳过、未过滤、未排除**。

根目录的 `test.xml` 是示例输入，**不是**测试用例，不计入 upstream_total。

## 参考资料
- [XML Indent 项目主页](http://xmlindent.sourceforge.net/)
- [上游 GitHub 仓库](https://github.com/penberg/xmlindent)
- [v0.2.18 源码归档](https://github.com/penberg/xmlindent/archive/refs/tags/v0.2.18.tar.gz)
