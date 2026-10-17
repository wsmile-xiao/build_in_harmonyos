# DRAFT-11055：waf testonly 测试套件在 OHOS 的执行分类与通过率对账（含 --disable-python 守卫）

- **触发实例**：tdb 1.4.15 适配（2026-09-16，任务 11055，分支 feat/tdb-1.4.15）
- **错误签名**：`Python test failed: PYTHONPATH=bin/python python3 python/tests/simple.py` + `python testsuite returned 1` + `make: *** Error 1`
- **类别**：testing（waf/samba 测试执行）
- **严重度**：2（测试误判红；不影响产物，但污染通过率对账）

## 症状（可复现）

以 `--disable-python` 构建纯 C 库后，`make test` 在 C 测试全过的情况下仍失败：

```text
...tdb1-run-circular-chain
...tdb1-run-circular-freelist
...tdb1-run-traverse-chain
testsuite returned 0
Running Python test with python3: python/tests/simple.py
Python test failed: PYTHONPATH=bin/python python3 python/tests/simple.py
python testsuite returned 1
make: *** [Makefile:17: test] Error 1
```

## 根因

`wscript` 的 `testonly` 是固定四段流水线：

1. 2 个 shell 集成测试（`test_tdbbackup.sh` / `test_tdbdump.sh`）；
2. `tdb1_unit_tests` 列表内的 TAP 二进制逐个执行（输出重定向到 `test-output`，失败才 cat）；
3. `tdbtorture` 多进程压力测试（返回码即结果）；
4. `RUN_PYTHON_TESTS(['python/tests/simple.py'])`。

第 4 段不感知 `--disable-python`：`SAMBA_CHECK_PYTHON` 即使禁用绑定也会把 `python3`
记入 `env.python_interpreters`，于是 `make test` 仍运行 pytdb 绑定测试；而
`--disable-python` 时 pytdb 未构建，`import tdb` 失败 → 整个 `make test` 判红。
此外逐项通过率**不能**从 stdout 直接读：TAP 二进制只打 `...<name>` 进度行，单测
细节被重定向进 `test-output`。

## 最小修复（平台无关）

给 `testonly` 加配置守卫（不改任何上游测试用例）：

```python
    if env.disable_python:
        print("python testsuite skipped (--disable-python)")
        pyret = 0
    else:
        pyret = samba_utils.RUN_PYTHON_TESTS(['python/tests/simple.py'])
        print("python testsuite returned %d" % pyret)
    sys.exit(ecode or pyret)
```

修复后 `make test` rc=0，且在输出中留下显式跳过记录（可被 PR 报告引用）。

## 通过率对账方法（真实证据口径）

- **TAP 单测**：`grep -c '^\.\.\.tdb1-'` 的计数必须与 `wscript` 的
  `tdb1_unit_tests` 列表长度一致（tdb 1.4.15 = 37）；两者对账可发现"少跑/静默跳过"；
- **shell 集成**：计数 `success:` 行（本包 6 行，覆盖正常/只读备份与 dump 比对）；
- **压力测试**：`testsuite returned 0`；
- **python 绑定测试**：输出 `python testsuite skipped (--disable-python)`，在 PR 中
  如实标注为"未启用（可选绑定）"，并给出技术原因，不得计入"通过"或写成"上游无测试"。

## 真实验证

tdb 1.4.15 设备实机 `make test` rc=0：37/37 TAP + 2/2 shell + tdbtorture 通过；
`conan create`（内含 `make test`）全量通过。

## 禁忌

- ❌ 注释/删除 `RUN_PYTHON_TESTS` 调用，或 stub 一个假 `tdb` 模块"制造通过"（R9）；
- ❌ 把未运行的绑定测试写进"通过率"或笼统写"上游无测试"（欺骗性对账）；
- ❌ 改上游测试用例来适配（本问题只需执行侧守卫）。

## 适用范围与边界

- **适用**：waf/samba 系独立包（tdb/talloc/ldb/tevent）在 OHOS 的上游测试执行与
  PR 测试账本；`testonly` 结构和 `RUN_PYTHON_TESTS` 行为在各包 `wscript` 间高度同构。
- **边界**：若上游未来版本自行处理 `--disable-python`（不再记录 python_interpreters
  或守卫第 4 段），本补丁即可撤销；启用 pytdb 的包不适用该守卫（应修复 python
  工具链后运行绑定测试）。

## 与现有知识库的关系（查重）

| 既有条目 | 内容 | 本条增量 |
|---|---|---|
| **E339**（waf imp/模块级） | 旧版 waf 启动崩溃修法 | 无关（不同阶段：启动 vs 测试执行） |
| **E192**（musl robust mutex） | 条件编译修法 | 无关（本包自动探测；mutex 单测在降级模式下全过，属测试分类事实） |
| E252/E239（消费者测试断言） | test_package 怎么断言 | 正交：本条讲**上游 waf 测试流水线的执行与对账**，不是消费者测试 |
| E193（HMDFS 大小写敏感测试跳过） | 单测逐个跳过先例 | 本条讲的是"整套 python 绑定测试在禁用时的显式守卫 + 计数对账"，且强调不得静默跳过 |

`draft-review` 预审（2026-09-16，knowledge/graph/index.tsv 766 条）：质量预检 signature/root_cause/rec 全 ✅；TOP5 相似度 E318=0.08、E413=0.07、E308=0.07、E410=0.05、E327=0.05（均仅类别弱重合，sig/kw 全 0）→ **预审建议 create（疑似新知）**。
