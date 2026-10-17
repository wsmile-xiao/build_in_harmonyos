# trinculo 0.96 Python2 测试驱动 py3 移植与 golden MD5 跨平台全等（草稿 E711）

- **来源**：trinculo 0.96 OHOS 移植（任务卡 11293），W0 测试面预核
- **日期**：2026-09-24
- **证据**：`archives/t/trinculo/0.96/notes.md` 问题表 #2；`$TASK_DIR/w0/testing-run1.log`（9/9 PASSED）

## 症状

```
$ python3 bin/testing.py
  File "bin/testing.py", line 14
    print "Testing trinculo (v0.95)"
SyntaxError: Missing parentheses in call to 'print'
```

上游 `bin/testing.py`（2016）是 Python2：print 语句（含尾逗号形式
`print "N. Testing…",`）、`file()`、MD5 比对用 str 字面量。设备与 CI 均无
python2——若不处理，上游 9 用例面在任何环境都跑不起来（NOT_RUN）。

## 根因与移植法

生态 python3-only vs 上游 py2 驱动。**机械四改、逻辑零改动**：

1. `print "x"` → `print("x")`；尾逗号 → `print("x", end="")`
2. `file(p)` / `file(p,"w")` → `open(p, 'rb')` / `open(p,"w")`
3. `hashlib.md5(open(p)).read()` → 二进制读 `open(p, 'rb')`
4. 比对字面量 `'\x3d\x36…'` → `b'\x3d\x36…'`

测试逻辑、场景顺序、全部 golden MD5 常量**一个字节不改**。

## 关键收益：golden 断言保留而非删除

移植后沙箱 HOME 实跑 **9/9 PASSED**——每个用例三段断言（rc / 产物存在 /
**golden MD5 字节比对**）全过，即 aarch64 OHOS clang15 `-O3` 产物与上游
2016 x86 期望**字节全等**。这证明数值输出格式跨平台稳定，字节级回归面
**保留**。常见错误做法是"平台不同 → 删 MD5 断言"，把最强判据削弱成存在性
检查；正确顺序是**先实测再决定去留**（本例实测全等 ⇒ 保留）。

计数口径（四口径不混用）：断言口径 N=27 = 9 用例 × 3 断言，与脚本 27 个
FAILED 分支一一对应；用例口径 9；Debian run-unit-test 同为 9 场景互证。

## 验证

```bash
python3 -m py_compile bin/testing.py                      # → rc=0
HOME=$TASK_DIR/test-home TMPDIR=$TASK_DIR/test-home python3 bin/testing.py
# → 1..9 全 PASSED（含 golden MD5 字节比对），$TASK_DIR/w0/testing-run1.log
```

## 禁行

- 删/跳过 golden MD5 断言：跨平台全等已实测，删=削弱回归面（W4 少报质疑）。
- 改 golden 常量去迁就产物：数值真漂移时会静默掩盖。
- 留 py2 驱动等环境：设备/CI 无 python2，上游面永远 NOT_RUN。

> 提交后回填 source_commit；晋升需人工/AI 评审改名 `E711.kv` 移入 `knowledge/graph/` 并登记 index.tsv。
