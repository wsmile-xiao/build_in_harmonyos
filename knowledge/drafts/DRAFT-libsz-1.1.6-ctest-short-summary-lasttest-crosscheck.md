# DRAFT-libsz-1.1.6-ctest-short-summary-lasttest-crosscheck
> 兼容精简版ctest短格式汇总行的容错解析与LastTest.log交叉验证

## 问题特征（真实日志片段/标记）

- `HMBS_UPSTREAM_TEST_RESULT={"status": "failed", "framework": "ctest", "command": "ctest --output-on-failure", "discovered": 7, "executed": 0, "passed": 0, "failed": 0, "skipped": 0, "reason": "exit 0 but no ctest summary line in harness output"}`
- `libsz/1.1.6: ctest file evidence: file=/storage/Users/currentUser/preflight/clients/68c6c75a2994/conan-home/p/b/libszca06bd26846e3/b/build/Release/Testing/Temporary/LastTest.log bytes=1861208 passed_in_file=0 failed_file=empty/missing total_time=missing`
- `HMBS_UPSTREAM_TEST_RESULT={"status": "failed", ... "reason": "exit 0 but no ctest summary line in harness output; file=.../LastTest.log bytes=1861208 passed_in_file=0 failed_file=empty/missing total_time=missing"}`
- 决定性证据轮透出 `ctest summary-line: 100% tests passed out of 7`，`ctest=/storage/Users/currentUser/.harmonybrew/bin/ctest`，`raw_bytes=876` 对比 `LastTest.log bytes=1861208`。
- 前序 `v2:compile:temporary_directory_readonly` 已在 attempt 44553 消除，流程进入 `v2:upstream_test:test_assertion_failed` 后同一指纹稳定复现三轮。

## 根因

真机 `~/.harmonybrew/bin/ctest` 为 shim/精简版：stdout 只保留 876 字节精简行，汇总行为短格式 `100% tests passed out of 7`，无标准长格式 `, 0 tests failed` 中段，1.8MB 详情只落盘 `Testing/Temporary/LastTest.log`。前两轮 harness 摘要正则强制要求 `, N tests failed` 中段故永不匹配，把 exit 0 且 Total Test time 约 53s 的已跑完套件误判为 `exit 0 but no ctest summary line`，`discovered=7/executed=0`。仅加固 stdout 空白/ANSI 容忍（attempt 44570）与仅引入落盘文件但仍用旧正则（attempt 44585，`passed_in_file=0 total_time=missing`）均不能命中短格式，属重复已失败策略。

## 修复方案（rec）

上游测试与用例口径零改动，仅改 `archives/l/libsz/1.1.6/conanfile.py` 的 harness 解析与证据逻辑：

1. stdout 与 `LastTest.log` 两处摘要正则把 `, N tests failed` 改为可选组，兼容长短两种格式；短格式下以 `percent==100` 判定零失败，`percent<100` 或总数不等于发现数照旧失败。
2. 子进程按字节捕获后 `errors=replace` 解码，剥 ANSI、去 `\r` 后用空白容忍正则匹配摘要，逐用例 `Passed` 判定同样走归一化输出。
3. 跑 `ctest` 前删除 `Testing/Temporary` 下陈旧 `LastTest*.log`，保证文件证据属于本次运行；stdout 缺逐用例行时用 `LastTest.log` 交叉复核，要求全部 7 个用例在 stdout 与文件合并文本中均有 `Passed` verdict、`LastTestsFailed.log` 为空、`Total Test time>0`，四重齐备才判 pass 并记录文件证据行，否则 fail-closed。
4. 失败日志输出 `ctest` 路径/目录/rc/字节数/摘要行/verdict/尾部日志的结构化诊断；本地 `py_compile` 与长/短/失败三种摘要自测通过后送真机预检验证（attempt 44599 通过全部门禁）。

## 禁止策略

- 禁止在 `executed=0` 或缺逐用例 `Passed` 时仅凭短格式百分比伪造通过：`HMBS_UPSTREAM_TEST_RESULT={"status":"passed"..."executed":0` 不允许放行；须逐用例 `Passed` 齐备且与 `LastTest.log` 交叉验证，否则保持 fail-closed。
- 禁止用上次落盘冒充本次：陈旧日志必须先删；时长为 0 或任一用例缺 `Passed` 仍判失败，静默跳过不得计为通过；不修改上游测试内容。

## 与相近条目的边界（查重）

- 现有 `readonly_tmp`/`tmpdir` 重定向条目只解决 clang 临时文件落只读 `/tmp`、conan buildenv 隔离致 `TMPDIR` 未继承、`CMAKE_SYSTEM_NAME=HarmonyOS` 未识别、工具链绝对路径不可执行等问题，均未涉及 ctest 汇总格式差异与落盘日志第二证据源。
- 本条目仅覆盖 `upstream_test:test_assertion_failed` 中 `exit 0 but no ctest summary line` 且实为短格式 `100% tests passed out of N` 的一类 shim-ctest harness 误判，不替代编译期临时目录与工具链修复。

## 适用判断

- 适用：`ctest` 退出码 0 且 `Total Test time` 存在，但 stdout 持续找不到汇总行；`ctest summary-line` 为 `100% tests passed out of N` 短格式；shim 版 ctest 精简 stdout、详情只落盘的场景；关键词 `ctest_short_format`、`100% tests passed out of`、`no ctest summary line`、`lasttest.log`、`hmbs_upstream_test_result`。
- 短格式仅在 `percent==100` 且总数等于发现数且逐用例 `Passed` 齐备且 `LastTestsFailed` 为空且时长大于 0 时判过；若下轮出现无 `Passed` verdict 的用例，需全量 876 字节 stdout 排查而非放宽阈值。
