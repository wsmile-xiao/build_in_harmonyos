# lapack64 3.12.1 测试报告（reports/test-report.md）

## 上游测试（真机，R51 三步法）

- 套件：上游 LAPACK testing（LIN + EIG + MATGEN），14 驱动 × 74 次运行（消耗 47 个不同输入文件；上游 .in 清单共 67 个，bak/bal/dmd 等 20 个不在默认全量内），ILP64 模式（flang -fdefault-integer-8），TIMER=NONE，dlamch -O0 探针真机运行正常。
- 结果：**TOTAL=5151370 PASS=5151370 FAIL=0 SKIP=0 NOT_RUN=0**（官方 lapack_testing.py 汇总口径：nb test run / numerical error / other error；数值错误 0、其他错误 0）。
- 证据：reports/lapack64-upstream-testing-log.md（逐字转写 + 原件哈希索引）。

## 消费者测试（W3 conan create 内）

- test_package/test.c：int64 参数直调 dgemm_/dgesv_，2 断言（手算值校验），全链链接 liblapack64+libblas64+FortranRuntime+FortranDecimal。
- 结果：**TOTAL=1 PASS=1 FAIL=0 SKIP=0 NOT_RUN=0**（.ci-result.json exit_code=0；finish ci-metadata L1 "test_package executed" pass）。

## 门禁记录

| 门禁 | 结果 |
| --- | --- |
| L0 结构检查 | pass |
| L1 test_package | pass（executed） |
| L2 smoke（无 bin/，纯静态库） | skip |
| L4 补丁检查 | pass（patches: {}，无补丁） |
| L5 产物基线 | pass（lib/ 非空） |

计数单位说明：上游计数 = runner 汇总的测试运行数（每条数值校验 1 项）；消费者计数 = 测试程序数（1），断言 2 项另行说明，不与上游混加。
