# DRAFT-liborcus-0.21.0-automake-summary-spacing-xfail-pass
> automake test-suite汇总双空格对齐解析修复与XFAIL计入通过，真机rc=0时避免零计数误判failed
## 问题特征（真实日志片段/标记）
- 真机upstream_test失败，`make check`返回rc=0但门禁判failed：`upstream make check failed (total=39 passed=0 failed=0 rc=0)`。
- 日志含automake双空格对齐行：`liborcus/0.21.0: [upstream] # FAIL:  0`（`FAIL:`后双空格），同组还有`liborcus/0.21.0: [upstream] # ERROR: 0`。
- 结构化标记误判：`HMBS_UPSTREAM_TEST_RESULT={"status": "failed", "framework": "automake-check", "command": "make check", "discovered": 39, "executed": 0, "passed": 0, "failed": 0, "skipped": 0, "total": 55, "excluded": 16}`。
- 修复后真机应为：`HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "automake-check", "command": "make check", "discovered": 39, "executed": 39, "passed": 39, "failed": 0, "skipped": 0, "total": 55, "excluded": 16}`。
## 根因
- `archives/l/liborcus/0.21.0/conanfile.py`中`_run_upstream_tests`用单空格正则`# (TOTAL|PASS|...): (\d+)`解析automake test-suite汇总。
- automake对个位数用双空格对齐（如`# PASS:  39`、`# FAIL:  0`），导致PASS/FAIL/SKIP等行全部漏匹配，total累加但passed/failed为0，status误判为failed。
- XFAIL属于TOTAL中的非失败项（预期失败），未计入通过会进一步造成计数口径偏差。
## 修复方案（rec）
1. 在`archives/l/liborcus/0.21.0/conanfile.py`的`_run_upstream_tests`中定位汇总解析两处：`summaries`定义与`finditer`匹配。
2. 将两处正则分隔符由单空格改为`\s+`，即改为`# (TOTAL|PASS|FAIL|SKIP|ERROR|XFAIL|XPASS):\s+(\d+)`，兼容单/双空格对齐。
3. 将XFAIL计入passed（预期失败不视为失败），保持TOTAL= PASS+FAIL+SKIP+XFAIL+XPASS+ERROR口径一致。
4. 保持未提交等待HMBS真机预检复验，确认日志出现`discovered 39 executed 39 passed 39 failed 0 rc=0`且无SKIP/FAIL残留；若存在XFAIL需复核其确为预期失败语义。
## 禁止策略
- 禁止在rc=0且汇总含双空格行时直接输出`passed 0 failed 0 status failed`的零计数误判；必须先修复`\s+`解析再判定，否则掩盖39个TESTS真实通过。
- 禁止仅放宽门禁或删除断言来凑通过；不得用`discovered 0 status passed`零证据放行。
## 与相近条目的边界（查重）
- 查重表无任何automake汇总/XFAIL/SHELL命令行覆盖条目，本条为强增量。
- 相邻readonly_tmp/autoconf/getcwd条目阶段与签名均不覆盖：只读/tmp、编译器路径回退、shell分词、DESTDIR安装、头文件补齐均属compile/package阶段，本条仅覆盖testing阶段`automake-check`汇总解析与`HMBS_UPSTREAM_TEST_RESULT`计数口径。
## 适用判断
- 类可复用：automake test-suite汇总用`\s+`兼容单双空格并将XFAIL计入通过，属构建系统行为+证据门禁通用解法，适用于任何解析`# TOTAL/# PASS/# FAIL/# SKIP/# ERROR/# XFAIL/# XPASS`的配方。
- 适用当且仅当：`make check` rc=0但`HMBS_UPSTREAM_TEST_RESULT`出现`discovered>0 executed 0 passed 0 failed 0`，且原始日志可见`# FAIL:  0`类双空格行。
- 不适用：configure/编译探测失败、shell分词`cd src include`失败、libtool安装chmod缺失、test_package头文件缺失等非汇总解析问题。
