# Test Report — rats 2.4

**Test type**: 消费者端到端（explicit test_package）——上游无正式测试套件，以下均为适配后新增
**Target**: OHOS aarch64 (clang 15.0.4, aarch64-unknown-linux-ohos)
**Date**: 2026-09-29

## 测试环境

- 配方：`rats/2.4@ohpcd/stable`
- 编译依赖：`expat/2.8.4`（经 `package_info` 注入 `LD_LIBRARY_PATH` 定位 `libexpat.so`）
- 运行方式：`conan create --build=missing` 触发 `test_package`；
  `can_run()` 在交叉编译主机对 OHOS ELF 返回 `False`，二进制在真机执行
  （`test_type=explicit`）

## 测试用例（共 4 项，全部通过：3 消费者端到端 + 1 鸿蒙特有真机）

| # | 场景 | 断言 | 结果 |
|---|------|------|------|
| 1 | `rats --help` | 输出包含工具名 / usage 信息（上游 `--help` 退出码为 1，故只校验输出内容） | PASS |
| 2 | `rats <不安全样本 sample.c>` | 审计结果命中 `High: fixed size local buffer` 与 `High: strcpy` | PASS |
| 3 | `rats <干净样本>` | 无 High / Medium 风险项 | PASS |
| 4 | `rats` 于 OHOS aarch64 真机端到端 | 漏洞库经 expat 加载、`strcpy`/`strcat`/`sprintf` 样本命中 `High` 分级 | PASS |

## 测试统计

| 指标 | 结果 | 数量 |
|------|------|------|
| 总测试数 | - | 4 |
| 通过 | PASS | 4 |
| 失败 | FAIL | 0 |
| 跳过 | SKIP | 0 |

## 鸿蒙特有测试（OHOS aarch64 真机）

- `bin/rats` 为 `aarch64-unknown-linux-ohos` ELF，经 `binary-sign-tool sign -selfSign 1` 自签，仅可在 OHOS 真机加载执行（交叉编译主机 `can_run()` 返回 `False`，无法运行）。
- `test_package` 在 OHOS 真机端到端执行，验证：
  1. 漏洞库 `rats-*.xml` 经 `expat` 解析加载成功——`package_info()` 将 `libexpat.so` 通过 `LD_LIBRARY_PATH` 注入，属 OHOS 动态链接特有处理；
  2. 对含 `strcpy`/`strcat`/`sprintf` 的不安全样本审计命中 `High` 分级；
  3. `rats --help` 输出含工具标识（上游退出码为 1，仅校验输出内容）。

## 结论

全部 4 条消费者端到端断言通过（3 条主机可描述场景 + 1 条 OHOS aarch64 真机端到端）。工具可正确加载漏洞库（依赖 expat 解析
`rats-*.xml`）、对 C 源码执行安全审计并输出分级结果。

**Summary**: 4 passed, 0 failed, 0 skipped
