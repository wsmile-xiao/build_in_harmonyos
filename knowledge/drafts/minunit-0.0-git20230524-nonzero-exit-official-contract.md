# 测试框架自适配的退出码契约陷阱（minunit 0.0-git20230524）

> Draft: `DRAFT-MINUNIT-GIT20230524-NONZERO-EXIT-OFFICIAL-CONTRACT`
> Stem: `minunit-0.0-git20230524-nonzero-exit-official-contract` — 与同 stem 的 `.kv` 配对

## 基本信息

- **ID**: DRAFT-MINUNIT-GIT20230524-NONZERO-EXIT-OFFICIAL-CONTRACT
- **严重度**: 2
- **类别**: testing|conan|ci-gate
- **触发工具**: conan|ci
- **阶段**: testing

## 错误特征

适配"被测对象是测试框架本身"的库时，官方自测套件跑出：

```
11 tests, 11 assertions, 6 failures
exit=6
```

按"测试程序退出码非零 = 失败"的默认语义，conan `build()` 里 `self.run("./minunit_example")`
直接抛：

```
ERROR: minunit/0.0-git20230524: Error in build() method, line 55
 ConanException: Error 6 while executing
```

——而这次运行**完全符合上游设计**。

## 根因分析

minunit 的退出码语义是"失败计数"，不是"成功布尔"：

- `MU_EXIT_CODE` 宏展开为 `minunit_fail` 计数器；
- 官方自测套件 `minunit_example.c` 的 11 个 `MU_TEST` 中，6 个是**框架故意演示失败的用例**
  （`test_check_fail` / `test_assert_fail` / `test_assert_int_eq_fail` /
  `test_assert_double_eq_fail` / `test_string_eq_fail` / `test_fail`）——它们的用途正是
  验证断言捕获能力，"如期失败"才是正确行为；
- 因此一次完整正确的运行必然 `exit 6`。上游官方 CI 契约 `ci/check_example.sh` 白纸黑字：

```bash
expected_exit_code=6
./minunit_example
if [ $? -ne $expected_exit_code ]; then
  echo "Unexpected exit code: $expected_exit_code expected but was $?"
  exit 1
fi
```

**非 6 反而判 FAIL**。

两类对称的误判都要防：

| 错误做法 | 后果 |
|---|---|
| 不带 `ignore_errors` 直接 run | 一次正确运行被炸成 "Error 6 while executing"（误判失败） |
| 只 `ignore_errors=True` 不校验码值 | 码是 5 或 7（框架真坏了）也静默通过（误判成功） |

## 影响范围

- 所有"被测对象是测试框架本身"的包（minunit 及同类极简断言/测试库的 self-test）；
- 官方套件内嵌 designed-to-fail 演示用例的任何包；
- 在 conanfile `build()` / `test_package` 里包裹此类套件的配方；
- 把退出码当成功布尔的 CI 门禁与统计口径（rule4 高频打回点）。

## 推荐方案

**方法**: `assert-official-exit-contract-exactly`

1. **先读官方契约脚本再动手**：`.travis.yml`/`appveyor.yml` 的 script 段 →
   `ci/check_example.sh`，提取官方对退出码的精确期望（本例 `expected_exit_code=6`）。
2. **build() 内契约断言**：`self.run(cmd, ignore_errors=True)` 取回 retcode
   （Conan 2.x 语义：ignore_errors=True 时返回退出码不抛异常），精确断言
   `retcode == 6`，不符 `raise ConanException` 带期望值与实际值。
3. **消费者侧同法三重证据**：test_package 里故意失败用例数 N → 断言 `exit == N`，
   同时校验 `MU_REPORT` 输出行（`"10 tests, 10 assertions, 5 failures"`）与
   setup/teardown 触发计数（`setup_calls=10 teardown_calls=10`）——
   退出码 + 报告行 + 钩子计数三重断言，防"只对码漏对行为"。
4. **统计表如实写契约口径**：PR 统计表与 `test_package/MANIFEST.yml` 写明
   "官方契约口径：exit 6 == PASS（6 个 designed-to-fail 演示用例按设计失败）"，
   防止人工审查把非零退出码误读为通过率问题。

## 降级方案

若官方无显式契约脚本：先本地逐用例实测上游套件期望退出码（记录
`N tests / M failures / exit M`），按实测值断言；若实测不稳定（时序/环境相关的
失败数），退化为只断言 MU_REPORT 报告行格式 + 用例数与断言数一致，并在
notes.md 记录放弃码值断言的具体原因。

## 验证命令

```bash
cd <src> && clang -std=c99 -I. minunit_example.c -lm -o minunit_example && \
  ./minunit_example; echo "exit=$?"
# 期望: "11 tests, 11 assertions, 6 failures" 且 exit=6（官方契约 ci/check_example.sh）
```

## 取证记录

- 包: minunit 0.0-git20230524（archives/m/minunit/0.0-git20230524，PR !14375）
- 官方契约原文: 上游 `ci/check_example.sh`（expected_exit_code=6）
- 设备实测: OHOS clang15 -std=c99 编译零警告；运行 11 tests / 11 assertions /
  6 designed-failures / exit 6
- CI 验证: #68181 绿（build() 内契约断言真跑）；本地 conan create exit 0
- 消费者验证: test_package 10/10 PASS（exit==5 精确断言 + 报告行 + 钩子计数）
