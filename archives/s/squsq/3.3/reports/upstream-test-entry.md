# 上游测试入口核验 — squsq 3.3

> **原始日志说明（review-memory 规则 19）**：`*.log` 属仓库审查规则 19 定义的 **PR 禁止文件**，故本目录下的 `.log` 原件**不随 PR 提交**（保留在工作区本地）；本报告引用的日志名指本地原件，其**关键原始输出已内联于本报告**，结论可被独立复核。

**结论：上游（以及两个发行版 port）都不提供任何自动化测试入口。**
`make check` / `make test` 无处可跑；本包不伪造「上游测试」，改为按上游 readme 与源码
行为定义派生用例并全部实跑（见 `upstream-test-cases.md`）。

所有命令均为真实执行，原始输出与退出码见 `50-upstream-test-entry.log`（本地工作区原件，按规则 19 不随 PR 提交）。

## 1. tarball 文件清单（无构建/测试文件）

```
$ tar tzf t20-squsq-3.3.tar.gz
t20-squsq
t20-squsq/lusq.exe
t20-squsq/makesq.mic
t20-squsq/makeusq.mic
t20-squsq/readme
t20-squsq/sq.c
t20-squsq/sq.h
t20-squsq/sqcom.h
t20-squsq/sqdbug.c
t20-squsq/sqio.c
t20-squsq/tr1.c
t20-squsq/tr2.c
t20-squsq/usq.c
t20-squsq/usq.h
t20-squsq/utr.c
exit=0

$ tar tzf t20-squsq-3.3.tar.gz | grep -iE 'makefile|cmakelists|configure|meson|test|spec|\.sh$'
（无输出）
grep exit=1        # 1 = 无任何命中
```

15 个条目里：10 个 C 源/头文件、1 个 readme、2 个 TOPS-20 MIC 构建脚本、1 个 1988 年的
TOPS-20 可执行文件 `lusq.exe`。**没有 tests/ 目录、没有测试源文件、没有任何构建系统文件。**

## 2. 源码里没有测试框架

```
$ grep -rnE '\b(test|check)\b' *.c *.h
sq.c:36:  * to be incorrect and fail the USQ crc check.
sq.c:61:  * able to check for whether the output file name it creates is valid
sq.c:193: if (strlen(outfile) + 3 > FNM_LEN) {  /* check for long file name */
usq.c:19: *   No CRC check is performed when previewing.
sqcom.h:21:EXTERN unsigned int crc;  /* error check code */
```

全部命中都是**注释**（CRC 校验、文件名长度检查），没有任何 assert、测试驱动、
测试宏或 `main()` 之外的测试入口。

## 3. `make check` / `make test` 无目标

```
$ make -n check
make: *** No rule to make target 'check'.  Stop.
exit=2

$ make -n test
make: *** No rule to make target 'test'.  Stop.
exit=2
```

（源码目录里本就没有 Makefile —— Unix 侧的 Makefile 由发行版 port 提供。）

## 4. 发行版 port 也没有测试目标

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| FreeBSD `files/Makefile` | `grep -nE '^(check\|test\|regress\|do-test)' evidence/freebsd_port_files_Makefile` | 无命中（该文件只有 `all: sq usq`、`sq: sq.o tr1.o tr2.o sqio.o`、`usq: usq.o utr.o` 三条规则） |
| FreeBSD port `Makefile` | `grep -nE 'TEST_TARGET\|do-test' evidence/freebsd_port_Makefile` | 无命中（无 `TEST_TARGET`、无 `do-test`） |
| NetBSD pkgsrc `Makefile` | `grep -nE 'TEST_TARGET\|do-test\|REGRESS' evidence/netbsd_pkgsrc_Makefile` | 无命中（无 `TEST_TARGET`、无 `do-test`） |

## 5. 可用的「上游样例」是什么

上游没有测试程序，但有两份**权威行为描述**，本包的用例全部由此派生：

1. `readme`（tarball 内，作者 Frank J. Wancho）中的 *Changes to SQ* 1–4 与
   *Changes to USQ* 1–4；
2. `sq.c` / `usq.c` 的 usage 文本与 `main()`/`obey()` 的选项处理
   （`-`、`-<n>`、`-F`、歧义名拒绝、8.3 输出命名、`FNM_LEN` 截断），
   以及 `sqio.c` / `tr2.c` / `utr.c` 实现的 Squeeze 头部磁盘布局。

> 这些不是「上游附带的测试」，而是把上游写在文档/源码里的行为逐条变成可执行断言。
> 逐条用例、命令、结果与日志见 [`upstream-test-cases.md`](upstream-test-cases.md)。

## 6. 未修改上游测试的原因

上游没有任何测试文件，因此本包**不存在对上游测试用例的修改或跳过**：
`upstream_tests: []`、`upstream_test_in_build: false`（见 `test_package/MANIFEST.yml`）。
唯一可运行的验证载体是 `test_package/`，它按 R34 要求真实调用被测包产出的
`bin/sq`、`bin/usq` 二进制，不是空壳测试。
