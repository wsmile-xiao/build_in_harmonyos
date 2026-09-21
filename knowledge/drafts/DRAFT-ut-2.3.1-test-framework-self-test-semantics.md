# 测试框架自测二进制的"故意失败"输出语义（DRAFT-ut-2.3.1-test-framework-self-test-semantics）

> 草稿编号: DRAFT-ut-2.3.1-test-framework-self-test-semantics（.md/.kv 配对）
> 来源: ut 2.3.1 R01 完整适配（executor pc5-6, 2026-09-19, task_id ut-2.3.1-r01-pc5-6-20260919T134255Z）

## 问题

把 header-only 测试框架库（boost-ext/ut 型）适配到 HarmonyOS 时，运行其自测二进制
`ut_test` 后 stderr 输出：

```
tests:   13 | 7 failed
asserts: 9 | 2 passed | 7 failed

libc++abi: terminating
```

表面上像是测了 13 个用例、7 个失败、还 abort 了——若据此判定框架自测失败，
会错误阻塞适配、错误写台账，甚至误报 failed_test。

## 根因

测试框架的自测源（如 `test/ut/ut.cpp`）会用 `ut::cfg<ut::override> = fake_cfg{}`
覆盖框架 runner，**故意**注册：

- 失败断言（`events::assertion<bool>{.expr = false}`）——验证框架能检测并报告失败；
- 异常事件与 `std::abort()` 处理用例——验证框架的 abort 检测；该用例经
  `fork()` 子进程执行，子进程的终止信息（`libc++abi: terminating`）打在
  stderr 上，父进程只观察子进程状态，继续返回 0。

因此 stderr 的失败摘要 + terminating 是**框架自测的预期输出**，不是该二进制的真实失败。

## 方案

1. **通过判据 = 主进程退出码 + ctest 判定**：`./test/ut/ut_test; echo $?` 期望 0；
   `ctest --output-on-failure` 期望 100% passed。两者都对则自测通过。
2. stderr 的 `tests: N | M failed` 摘要与 `libc++abi: terminating` 如实记入
   测试台账"说明"栏，不计入失败数。
3. 用户测试源（如 `test/ft/` 的 suite）仍按真实结果判定（`All tests passed (N asserts
   in M tests)`、exit 0）。
4. 未实例化入口（如 `win_compat_test` 的 WIN32 互斥分支）按平台互斥如实列台账，
   不得写成失败或已通过。
5. 双口径统计照常分开表述：
   `executed_passed_total/source_declared_total` 与 `executed_passed_total/configured_executable_total`。

## 验证（ut 2.3.1 实测）

| 命令 | cwd | exit_code | 结果 |
|---|---|---|---|
| `cmake -S . -B build-ctest -DBOOST_UT_BUILD_TESTS=ON -DBOOST_UT_ENABLE_RUN_AFTER_BUILD=NO -DCMAKE_CXX_STANDARD=20` | 源码根 | 0 | 配置成功 |
| `cmake --build build-ctest -j8` | 源码根 | 0 | ut_test/ft/ft-no-exceptions/ft-link 构建成功 |
| `ctest --output-on-failure` | build-ctest | 0 | 4/4 Passed（100%） |
| `./test/ut/ut_test` | build-ctest | 0 | stderr 预期失败摘要，exit 0 |
| `./test/ft/ft` | build-ctest | 0 | All tests passed (6 asserts in 4 tests), 2 tests skipped |

上游 CI（.github/workflows/linux.yml）同口径（`BOOST_UT_ENABLE_RUN_AFTER_BUILD=NO` + `ctest`）全绿，
佐证该判定口径与上游一致。

## 适用边界与反例

- **适用**：框架自身自测二进制（ut_test 型）的输出解读；同类测试框架（doctest/catch2）
  自测出现类似故意失败输出时同样适用。
- **反例**：用户测试源或 test_package 消费者测试出现失败（exit != 0 或 ctest fail）时，
  不得以"自测语义"为由豁免——必须如实报失败并修复。

## 关联

- 相关正式条目：E321/E322/E470（header-only 配方模式，非本语义）
- 触发条目：无（四范围查重未命中）