# DRAFT-skint-0.6.8: 上游测试“只打印汇总、不设退出码”导致的测试假绿

Status: DRAFT
Source: skint 0.6.8（false-schemers/skint，tag v0.6.8）
PR: 【知识库扩展】feat(skint): 0.6.8 适配 HarmonyOS PC（分支 feat/skint-0.6.8）

## 相关既有条目

撞库命令与结果（2026-10-02）：

```
python3 scripts/ohc-run.py engine "out of N passed 退出码 0 测试假绿"    -> E370（Meson 嵌套 fixture 的“进程成功≠子用例全过”）
python3 scripts/ohc-run.py engine "上游测试打印汇总 不设置退出码"        -> E535（CGNS：路径 A 未启用上游 CTest 就写 0/N）
grep -Ein "test-end|out of .* passed|假绿" knowledge/graph/index.tsv     -> 无直接命中
grep -REil "假绿|退出码|harness" knowledge/doc/                          -> 未发现覆盖“harness 不设退出码”机制
```

| 条目 | 已覆盖内容 | 本草稿增量 |
|---|---|---|
| E370 | Meson 嵌套 fixture：**进程成功**不代表源码声明的平台 skip 之外全部通过；JSONL 里有 expected-failure | E370 面向 **Meson/ctest 系**的嵌套 runner 与 JSONL 计数；本条面向**自研 stdout 汇总型 harness**（Scheme/Perl/shell），增量是“退出码压根不反映失败”这一机制，并给出 `passed==run` + `run>=基线` 的双重判据 |
| E535 | 路径 A 以“上游测试不可用”为由写 0/N，未真正启用上游 CTest | E535 是**没跑**上游测试；本条是**跑了但只看 rc**，属于“跑了却判错”；两者一起构成测试门禁的两类漏洞 |
| P013 | 平台限制必须降级而非绕过 | 本条把该原则落到“测试门禁口径”上：不许靠删测试/短路让门禁变绿 |

结论：现有条目未覆盖“harness 只打印不返回”这一机制，可独立申报；相近条目填入 `similar_to`。

## Scope

适用：

- 上游测试套件把失败统计**只写到 stdout**，进程退出码不反映失败（自研 runner、Scheme/Perl/shell 脚本、Makefile 的 `test` 目标没有 `; exit $$fail` 之类收尾）；
- 构建/CI 门禁以“命令退出码为 0”或“日志里出现 `passed`/`100%`”作为通过判据。

不适用：ctest/pytest/gtest 等框架本身以非零退出反映失败的项目（那些可直接看 rc，但仍需防“少跑”）。

## Symptom

把 skint 0.6.8 上游一致性套件 `test/test.scm` 的**一处**期望值故意改错后运行：

```
$ sed 's/(test 1764 (square 42))/(test 9999 (square 42))/' test/test.scm > /tmp/t.scm
$ ./skint /tmp/t.scm > /tmp/t.log 2>&1; echo "rc=$?"
rc=0
$ grep -c '\[FAIL\]' /tmp/t.log
2
$ tail -1 /tmp/t.log
1192 out of 1194 passed (99.83%)
```

两条 `[FAIL]`、通过率 99.83%，**进程退出码仍是 0**。只判 rc 的门禁会直接放行。

（该处测试在套件中出现两次，故 `[FAIL]` 计数为 2；结论不受影响。）

## Root Cause

上游 harness 把“统计”和“进程状态”分开实现（`test/test.scm`）：

```scheme
(define (test-end)
  (write *tests-passed*) (display " out of ") (write *tests-run*)
  (display " passed (") ... (newline))
  ;; ← 没有 (exit)，也没有任何失败计数向外传递
```

- 失败只体现在打印出来的 `N out of M passed` 与 `[FAIL]` 行里；
- 进程状态永远 0，所以 `rc==0` 只说明“脚本跑完了”；
- 反向也不安全：若平台条件把某个子套件整个短路，套件仍会打印一个 **100% 的小分母**，
  于是“grep 100%”也拦不住静默少跑。

## Recommended Fix / Workaround

门禁按“解析 + 基线比对”两条一起判：

1. 从输出里抓汇总行 `(\d+) out of (\d+) passed`，取最后一条；
2. 要求 `passed == run`（拦部分失败）；
3. 要求 `run >= 上游基线用例数`（拦静默少跑）；
4. **解析不到汇总行 = 失败**（拦“没跑/输出被吞”）。

skint 0.6.8 归档里的落地形态（`build()` 内，`conanfile.py`）：

```python
SUMMARY_RE = re.compile(r"(\d+) out of (\d+) passed")
m = SUMMARY_RE.findall(log_text)
run, passed = (int(m[-1][1]), int(m[-1][0])) if m else (0, 0)
if not m or passed != run or run < R7RS_CASES_BASELINE:      # 基线 1194
    raise ConanException("上游 R7RS 一致性套件未全通过：%d/%d" % (passed, run))
```

同一配方里第二个套件（`test/srfi/all.scm`）**恰好**把失败数用作退出码，所以那里额外要求
`modules >= 111` 且 `CUMULATIVE FAILURES == 0`——两套口径都写进 `MANIFEST.yml`，避免混用。

## Fallback

上游 harness 不可改时，加一层 wrapper 在配方侧判定后再回到退出码：

```bash
./skint test/test.scm > log 2>&1
python3 - <<'PY'
import re, sys
t = open('log', encoding='utf-8', errors='replace').read()
m = re.findall(r'(\d+) out of (\d+) passed', t)
sys.exit(0 if m and m[-1][0] == m[-1][1] else 1)
PY
```

## Forbidden Approaches

| 禁止写法 | 原因 | 后果 |
|---|---|---|
| 只判 `rc==0` | harness 不把失败反映到退出码 | 部分失败直接判绿 |
| 只 `grep "100%"` | 静默少跑也会打印 100% 的小分母 | 少跑与失败都被放过 |
| 删除 / 跳过 / 注释掉上游测试目标 | 达标要靠真实运行（R9/R51） | 覆盖被削，PR 以“测试减少无正当理由”被拒 |
| `... \|\| true`、`; exit 0` 收尾 | 恒真短路 | CI 失去意义 |

## Verification

```bash
# A) 复现假绿（故意改错一处期望值）
sed 's/(test 1764 (square 42))/(test 9999 (square 42))/' test/test.scm > /tmp/t.scm
./skint /tmp/t.scm > /tmp/t.log 2>&1; echo "rc=$?"; tail -1 /tmp/t.log
#   期望：rc=0 且 “1192 out of 1194 passed” → 证明 rc 不可信

# B) 门禁判据在真实（未改动）套件上必须通过
./skint test/test.scm | tail -1        # 1194 out of 1194 passed (100%)

# C) 配方门禁在 A 的日志上必须失败
#   （把 /tmp/t.log 喂给上面的解析逻辑：passed != run → ConanException）
```

## Prevention

- 适配前读上游 harness 的“收尾函数”（`test-end`、`pass`/`fail` 统计、Makefile `test` 目标），
  确认失败是否反映到退出码；不反映就必须走解析 + 基线判据。
- `MANIFEST.yml` 里把**计数口径**与**基线用例数**一起写死，并声明“解析不到汇总行即失败”。
- 若上游同时存在多套测试（不同粒度），每套各自给一条判据，不要把两套口径混成一个数字。

## References

- 最小复现与真实日志：本 PR `archives/s/skint/0.6.8/test_package/MANIFEST.yml`、
  `archives/s/skint/0.6.8/notes.md`（“上游测试清点”小节）
- 上游 harness：`https://github.com/false-schemers/skint/blob/v0.6.8/test/test.scm`
- 同族：`E370`（Meson 嵌套 fixture）、`E535`（未启用上游测试）、`P013`（平台限制降级而非绕过）
