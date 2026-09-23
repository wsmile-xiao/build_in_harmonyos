# theft 0.4.5.1 测试报告

**测试日期**: 2026-09-05
**测试环境**: OpenHarmony PC aarch64, OHOS 6.0, clang 15, Conan 2.29.1
**测试对象**: theft/0.4.5.1

## 1. 上游测试

| 项目 | 结果 |
|---|---:|
| 上游测试库存 | 385 个 runtime test invocations |
| 实际执行 | 384 |
| 通过 | 384 |
| 失败 | 0 |
| 跳过 | 1 |
| 实际执行通过率 | 100%（384/384）|

执行命令：`make -j1 all test`

跳过测试：`forking_privilege_drop_cpu_limit__slow`。原因是 OHOS 不提供该测试依赖的 `RLIMIT_CPU` 到时信号行为；该测试仅在 `__OHOS__` 条件下跳过，其余上游测试全部执行并通过。

## 2. Conan 配方验证

执行 `conan create` 验证通过，包含以下门禁：

- G1 配方完整性：通过
- G2 干净构建：通过
- G3 系统同名库隔离：通过
- G4 产物完整性：通过
- L2 平台功能矩阵：通过
- L4 静态安全扫描：通过
- L5 产物基线检查：通过

## 3. 消费者测试

| 用例 | 目的 | 结果 |
|---|---|---|
| 1 | 通过 `theft_hash_onepass` 调用 theft API | PASS |

执行结果：1/1 通过。

## 4. 依赖

Conan `requires` 和 `tool_requires` 均为空。链接时使用系统库 `libm`，由 `cpp_info.system_libs = ["m"]` 声明。

## 5. 结论

`theft/0.4.5.1` 的 OHOS Conan recipe、上游测试和消费者测试均已验证通过，可进入 PR 审计流程。
