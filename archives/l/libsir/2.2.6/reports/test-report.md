# libsir 2.2.6 测试报告（R02 修正版）

> R02 依据上游测试入口普查与逐入口真实重跑修正统计。R01 报告 36 项为
> sirtests 默认运行自报口径（不含 performance、未构建 sirtests++），
> 本轮普查实测可运行上游入口 45 个，全部实际运行通过。

## 上游测试入口普查（R02）

| 入口组 | 注册表来源 | 注册条目 | 本轮实际运行 | 结果 |
|--------|-----------|----------|--------------|------|
| sirtests（C，默认运行） | tests/tests.c 行 41-76 | 36 | 36 | 全部 PASS |
| performance（--perf） | tests/tests.c:40（SIR_CL_PERFNAME） | 1 | 1 | PASS |
| sirtests++（C++） | tests/tests++.cc 行 44-51 | 8 | 8 | 全部 PASS |
| **合计（去重）** | | **45** | **45** | **全部 PASS** |

- 计数规则：按注册表入口名去重（37 + 8，无重叠 → 45）。
- sirtests 默认自报 `done: all 36 libsir tests passed in 3.300sec!`（RC=0）；performance
  `done: 1 libsir test passed in 2.875sec!`（RC=0）；sirtests++ `done: all 8 libsir
  tests passed in 0.001sec!`（RC=0）。
- 逐入口台账：每条入口独立 `--only <name>` 运行、独立日志 + SHA-256（见 R02 报告
  `upstream_test_entry_ledger` 与 `upstream_test_recount_rerun` 证据段）。

## 上游测试修改说明

对上游测试文件无修改（tests/ 下文件均为上游原样）。唯一源码补丁
`0001-src-sirinternal.c.patch` 修复 `sanity-thread-ids` 在 OHOS/musl 下
`pthread_setname_np("")` 返回 EINVAL 的平台差异：空线程名视为 no-op 成功
（无平台宏，glibc 行为不变）。该补丁使该入口由 R01 初次的 FAIL 恢复为 PASS。

## 消费者测试（test_package）

| 项目 | 结果 |
|------|------|
| 用例 | test.c（R34：实质调用 sir_makeinit/sir_init/sir_isinitialized/sir_getversionstring/sir_debug/sir_notice/sir_cleanup，含可失败断言） |
| CMakeLists | add_test(NAME test_libsir COMMAND test_libsir)，与 test.c 主程序一一对应 |
| conan-verify G2 | conan create PASS（含 test_package 构建与 L1 运行） |
| conan-verify G1/G3/G4 | PASS |

## 验证结论

- 编译状态：通过（clang 15.0.4 / OHOS armv8-aarch64 Release profile）
- 上游实际运行用例通过率：45/45（100%）
- 新增鸿蒙特有测试（test_package 消费者测试）：1/1（100%）
- 统计口径：上游合计 45（单元 45 = 普查去重）；适配后合计 46（上游实际运行 45 + 新增 1）