# DRAFT-parlay-0.11.0-go-test-exec-sign-column0-count
> OHOS下go test临时二进制-exec前自签名与column-0顶层诚实计数

## 问题特征（真实日志片段/标记）

- attempt 97459：`真机go test -v -count=1 ./... returncode=1，标记discovered=72/executed=0/passed=0/failed=0/skipped=72，主go build已成功`，`--- PASS/FAIL`为0的harness零执行。
- attempt 97477：`真机rule4 inconsistent：discovered 72，executed 83/passed 83，executed+skipped超出discovered；test.sh报cat: /tmp/parlay-neg-*.out: No such file`，另见`真机cat /tmp/parlay-neg-55325.out No such file`。
- 修复后：`parlay/0.11.0: parlay upstream \`go test -v -count=1 -exec <ohos-sign-wrapper> ./...\`: returncode=0 PASS=72 FAIL=0 SKIP=0`，含`=== RUN   TestEnrichSBOM_ErrorFetchingPackageData`等`t.Run`子测试输出，真机72/72通过。
- 关键词：`go test -exec` / `ohos sign wrapper` / `column-0` / `readonly_tmp` / `hmbs_repair_method`。

## 根因

1. 主`parlay`二进制与Go SDK已自签名，但`go test`在`GOTMPDIR`生成的临时`.test`二进制未经`binary-sign-tool`签名，被OHOS内核拒绝`fork/exec`，导致零`--- PASS/FAIL`行。旧逻辑用`skipped+=unaccounted`把72个未观测用例伪装成跳过且无`output tail`可查。
2. `conanfile`用`strip()`后判`--- PASS:`，把`go test -v`缩进的子测试（`t.Run`，如`enrich_cyclonedx`含子测试）计入，比`grep ^func Test`的72顶层多约11个，出现`executed 83 vs discovered 72`。
3. `test.sh`负例写死`/tmp/parlay-neg-$$.out`，在真机`TMPDIR=/storage/Users/currentUser/preflight/.../parlay-0.11.0/tmp`下重定向失败。

## 修复方案（rec）（编号步骤，含具体文件与命令）

1. `archives/p/parlay/0.11.0/conanfile.py`新增`_write_go_test_exec_wrapper`生成`go-test-exec.sh`，OHOS下以`go test -exec`在`exec`前对`$1`自签名后执行；OHOS时`go test`自动带`-exec wrapper`，非OHOS保持原命令。
2. 删除`skipped`算术补齐，保留原始`PASS/FAIL/SKIP`如实计数加`gaps`，并输出80行日志`tail`供下轮诊断。对应`HMBS_REPAIR_METHOD schemaVersion=1 title=OHOS go test临时二进制自签名+诚实计数`。
3. `conanfile _run_upstream_tests`改为`line.startswith`判定，仅计`column-0`顶层结果行，缩进子测试行排除；`notes.md`澄清`column-0`与72口径一一对应。对应`HMBS_REPAIR_METHOD title=Go顶层用例column-0计数+TMPDIR负例输出`。
4. `archives/p/parlay/0.11.0/test_package/test.sh`负例输出改为`${TMPDIR:-${TMP:-${TEMP:-/tmp}}}/parlay-neg-$$.out`并`mkdir -p`，`conanfile.py`沿用`SHELL=/bin/sh`调用。
5. 验证：真机`go test -v -count=1 -exec <wrapper> ./... returncode=0 PASS=72 FAIL=0 SKIP=0`，`executed/passed=72`与`discovered=72`一致。

## 禁止策略

- 禁止`executed=0.*skipped=72`：禁止把零执行伪装成72跳过放行，必须保留`returncode=1`与`executed=0`诚实标记并附日志`tail`。
- 禁止`executed 83 vs discovered 72`：禁止用`strip()`后匹配把缩进`t.Run`子测试计入顶层，必须用`column-0`单源计数。违者真机`rule4 inconsistent`退回。

## 与相近条目的边界（查重）

- 现有`readonly_tmp`命中为`test.sh`写死`/tmp`通用样板，本条将其扩展为`Go`负例`TMPDIR`三变量兜底，非通用替换。
- 现有`compiler_error`命中为异因异阶段条目（本任务97477阶段`compiler_error`实为计数口径问题，97517为`test.sh CRLF`致`set: -: unknown option`另案处理），不覆盖`-exec`签名。
- 现有`hmbs_platform_capabilities`命中为`shell/tmpdir/jobs`通用能力声明，无`-exec wrapper`签名方案覆盖。增量性成立。

## 适用判断

- 适用当且仅当：`HMBS_REPAIR_METHOD.applicableWhen`为`OHOS下go test临时二进制签名与含t.Run库的顶层计数`，即`go test -v`含`t.Run`子测试且总数按顶层`func TestXxx`盘点，`GOTMPDIR`临时二进制需签名才能`exec`。
- 不适用：纯`test.sh CRLF`致`/bin/sh unknown option`、无`go test`的`C/C++`库、非OHOS本地可直接`exec`场景。
- 真机72/72通过验证通用解法，类别性成立。
