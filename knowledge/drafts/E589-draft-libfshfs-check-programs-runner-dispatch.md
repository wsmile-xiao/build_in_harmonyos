# E589-draft-libfshfs-check-programs-runner-dispatch：注册数 vs runner 派发的上游测试计数口径

> 状态：DRAFT，路径 B（贡献创新）候选，最终分类与知识条目编号以官方审核为准
> 触发库：`libfshfs/20260130`（libyal 家族，Autotools 发布包）
> 主题：`make check` 只跑 TESTS runner，不等于 check_PROGRAMS 注册数；先清点注册数，再用上游 harness 补跑未派发程序，最后按两个单位分栏申报
> 编号：E589（编排方按 git 树口径复核保留；`tools/knowledge_id.py` 曾给出假空号 E565，详见 notes.md）

## 新增问题

libyal 家族（以及大量 Automake 项目）把单元测试注册在 `tests/Makefile.am` 的
`check_PROGRAMS`，真正决定"跑哪些、跑不跑"的是 `TESTS` 里的 shell runner：

- `tests/test_library.sh`：内部 `LIBRARY_TESTS`（30 个）+ `LIBRARY_TESTS_WITH_INPUT`
  （`support volume`，发布包无 `tests/input/` 时按上游规则退化为无参数执行）
- `tests/test_tools.sh`：内部 `TOOLS_TESTS` + `TOOLS_TESTS_WITH_INPUT`
- `tests/test_fshfsinfo.sh`：输入驱动，`tests/input/` 不存在 → `exit 77`

`libfshfs 20260130` 的 `tests/test_tools.sh` 把两个列表都写成空串：

```sh
TOOLS_TESTS="";
TOOLS_TESTS_WITH_INPUT="";
```

于是 4 个已注册（且已被 `make check` 编译出来）的 `fshfs_test_tools_*` 程序一个都没
被派发，automake 只看到 runner 以 77 退出并记成 SKIP。现场读数：

```text
$ grep -E '^# (TOTAL|PASS|SKIP|FAIL|ERROR)' tests/test-suite.log
# TOTAL: 3        ← 3 个 runner 脚本，不是 36 个测试程序
# PASS:  1
# SKIP:  2
# FAIL:  0

$ sed -n '/^check_PROGRAMS/,/^$/p' tests/Makefile.am | sed '1s/check_PROGRAMS *=//' | tr -d '\\' | wc -w
36               ← 注册数（上游当前 HEAD 同样是 36）

$ grep -c ' (PASS)' tests/test_library.sh.log
32               ← runner 真实派发并通过的程序数
```

即同一份构建里存在三个都"正确"却互不相同的数字：3（runner 汇总）、32（runner
派发）、36（注册）。任何只报其中一个的申报都会出问题：

- 只报 3（automake 汇总）→ 审方按上游 HEAD 的 `check_PROGRAMS` 清点得 36，
  命中"实测 N 大于声明 N"的少报红线；
- 只报 32（runner 派发）→ 漏掉 4 个已注册程序，同样少报；
- 直接写 36/36 而没有补跑证据 → 4 个程序根本没执行，等于谎报。

另一处易错点是**取数位置**：逐程序 `Testing: X (PASS)` 行不在 `make check` 的
stdout（automake 把 runner 输出重定向进日志），也不在 `tests/test-suite.log`
（那里只有汇总与失败时的日志转储），而在 `tests/<runner>.log`
（本包为 `tests/test_library.sh.log`）。在错误文件上 `grep -c ' (PASS)'` 会得到 0，
很容易被读成"程序一个都没跑"。

## 可复用方法

1. **先清点注册数**：`sed -n '/^check_PROGRAMS/,/^$/p' tests/Makefile.am | sed '1s/check_PROGRAMS *=//' | tr -d '\\' | wc -w`；
   同时取上游当前 HEAD 的同一清单（审方口径），取两者最大值作为 N 的下界。
2. **再看 runner 派发**：`grep -c ' (PASS)' tests/<runner>.log` + automake 汇总
   （`# TOTAL/# PASS/# SKIP/# FAIL`）。两者单位不同，必须分别记录。
3. **补跑已注册但未派发的程序**：不改上游用例源码，复用上游自带 harness——
   `. ./test_runner.sh` 之后调用 `run_test_with_arguments "Testing: tools_${n}" "./fshfs_test_tools_${n}"`。
   本包补跑 4 个，全部 PASS，程序级合计 36/36。若上游未来把列表填上，配方里的
   派发分支会自动跳过（判据：`TOOLS_TESTS="";` 与 `TOOLS_TESTS_WITH_INPUT="";` 同时出现）。
4. **分栏申报**：程序级 `TOTAL = check_PROGRAMS 数`；runner 级 `TOTAL/PASS/SKIP`
   取 automake 汇总；SKIP/NOT_RUN 逐条给技术原因（本包 2 个 SKIP = 空列表 runner、
   无 `input/` 夹具的输入驱动 runner，均 `exit 77`，属上游规则不是失败）。

## 与既有条目的边界

- `DRAFT-10251-libnfc-tools-1.8.0-autotools-test-framework-guard`：configure 守卫把
  整个测试目标从构建里排除（`TOTAL: 0`，"根本没构建"）。本条是**已构建、已注册**，
  只是 runner 列表为空导致未派发，差额是"少跑"而不是"没构建"。
- `DRAFT-no-upstream-tests-drive-real-interface`：上游确实没有测试套件时驱动真实接口。
  本条上游有 36 个注册程序，只是派发链缺口。
- `DRAFT-libfsntfs-release-archive-closure`：处理发布包闭包与 fixture 能力分层；
  本条只处理"注册数 ↔ 派发数"的计数与补跑口径，闭包审计不是主张对象。

## 证据

| 项目 | 内容 |
| --- | --- |
| 触发版本 | `libfshfs/20260130`（Debian orig tarball，sha256 `1d82c19f…`，上游 commit `dd100d2a…`） |
| 注册数 | `tests/Makefile.am` `check_PROGRAMS` = 36（上游当前 HEAD 同为 36） |
| runner 派发 | `tests/test_library.sh.log` 32 PASS / 0 FAIL；`test_tools.sh`、`test_fshfsinfo.sh` 各 SKIP(77) |
| 补跑 | 4 个 `fshfs_test_tools_*` 经上游 `run_test_with_arguments` 全部 PASS |
| 程序级合计 | TOTAL 36 = PASS 36 + FAIL 0 + SKIP 0 + NOT_RUN 0 |
| 复现命令 | 见 `.kv` 的 `verification_cmd`（全部落 `$TASK_DIR`，设备可直接执行） |
