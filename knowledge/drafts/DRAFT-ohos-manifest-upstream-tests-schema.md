# DRAFT: MANIFEST 测试字段名不匹配，生成器读不到，账目被判为全零

> 状态: 本地知识草稿，未提交、未发布、未关联任何远端。
> 本文档对应同一 stem 的 `.kv` 结构化版本，字段与 KV 逐字节语义配对。
> 范围声明：本文档是可复用的诊断证据与规则草稿；不声称创建了任何源码补丁、框架改动、远端 PR、Issue 或正式知识条目。
> 不含凭据、令牌、主机私有值、远端成功声明或不可验证证据链接。

## topic

`manifest.yaml` 里测试账目写成了**嵌套映射**（`test_results:` 下再放 `passed:`/`failed:`），而生成器与 CI 检查按**扁平字段**读取（`test_passed`/`test_failed`），于是真机实测出的通过数被读成 0，账目被误判为"全零"。字段名是接口，改完必须重新验证。

## error_signature

```
[WARN] 4. Manifest完整性: test_results 全零
```

而同一个 manifest 里明明写着实测 `passed: 513 / failed: 8`。特征是**manifest 内容看着很完整，检查器却说没有数据**。

## wrong_turns

1. **以为"测试没跑"**。实际跑了（有真机日志、有逐个程序的 Totals），是**读取侧**没读到。
2. **以为检查器坏了**。检查器按约定字段名读，是 manifest 没按约定写。
3. **只改字段名就收工**。字段一改，账目含义随之变化（N、passed/failed 的归属），旧验证结论不再对应新账目，必须重跑。

## root_cause

两侧约定不一致：

- **生成器侧**（`ci/tools/extract_upstream_tests.sh:176`）产出的键是扁平的

  ```yaml
  upstream_test_in_build: true
  upstream_test_command: "make check"
  upstream_tests:
    - file: example.c
      source: ...
      description: "..."
      command: "./example"
  test_package_tests:
    - file: test.c
      ...
  assertion_count: 0
  ```

- **CI 检查侧**（`scripts/ohc/submission.py:2164`）读的也是扁平键：

  ```python
  tr_passed = mf.get("test_passed", mf.get("test_results_passed", "0"))
  tr_failed = mf.get("test_failed", mf.get("test_results_failed", "0"))
  ```

- 而实际 manifest 写的是**嵌套**的 `test_results:` 映射（内含 `passed:`/`failed:`/`runtime_cases:`…）。检查器用的是简化 YAML 解析，取不到嵌套值，`get(...)` 落到默认 `"0"`，于是判"全零"。

写成 `tests:` 之类的另一个名字同样不会被识别——**键名是接口，不是注释**。

## detection

```
# 1) 看检查器到底读哪些键
grep -n "mf.get(\"test_\|test_results_passed\|test_results_failed" scripts/ohc/submission.py

# 2) 看生成器产出哪些键
sed -n '170,205p' ci/tools/extract_upstream_tests.sh

# 3) 看自己的 manifest 顶层键
grep -nE "^[a-z_]+:" archives/<x>/<ver>/manifest.yaml

# 4) 三者对齐：manifest 的键必须是检查器会读的键
```

## affected_scope

所有需要被生成器/CI 消费测试账目的配方 manifest。当前实例：`kcoreaddons5/5.116.0.1` 的 `manifest.yaml` 用的是嵌套 `test_results:`，其中记录了实测 524 个 runtime case（513 passed / 8 failed / 3 skipped）与 40 个可执行文件的逐个归类，但 CI 检查会读成 0。

## durable_solution

1. **以检查器读取的字段名为准**：账目字段用扁平键 `test_passed` / `test_failed`（兼容位 `test_results_passed` / `test_results_failed`）。
2. 上游测试清单用生成器产出的 `upstream_tests:` 结构（并区分 `test_package_tests:`），**test_package 不并入上游 N**。
3. **改完字段必须重新验证**：字段决定了账目语义（N 的分母、passed/failed 的归属）。字段变化后旧结论不再对应新账目，必须在新 HEAD 上重跑，保证 HEAD 与日志 SHA 一致。
4. 保留原始实测数据的详细块（逐程序归类、失败原因）作为**附加**信息，但不要把唯一入口放在生成器不认识的嵌套键里。

## verification

- 对齐后重新运行 CI 检查，`Manifest完整性` 一项不再报 `test_results 全零`。
- 手工核对：manifest 顶层键 ∩ 检查器读取键 ≠ ∅，且数值与真机日志一致。
- 重新验证后的日志 SHA 必须等于 manifest 与报告里写的 HEAD。

## recovery_condition

出现以下任一情况即应重新调查：检查器或生成器的字段名发生变更；manifest 加入新键但未被任何消费者识别；账目数值与真机日志不一致；HEAD 与日志 SHA 不再相等。
