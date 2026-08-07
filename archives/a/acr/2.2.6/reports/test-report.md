# acr 2.2.6 测试报告

> 测试日期：2026-08-06
>
> 测试类型：上游测试、Conan 消费者测试、OHOS armv8 配方验证、HarmonyOS PC 模拟器功能测试

## 测试摘要

| 测试集合 | 总数 | 通过 | 失败 | 通过率 |
|---|---:|---:|---:|---:|
| 修复后的上游 triplet | 12 | 12 | 0 | 100% |
| 上游 examples | 18 | 18 | 0 | 100% |
| 新增消费者场景（Linux 与模拟器重复执行同一组） | 3 | 3 | 0 | 100% |
| 合计（按不重复场景计数） | 33 | 33 | 0 | 100% |

原始上游结果为 29/30；路径 B 修复后为 30/30。消费者测试没有替代或计入
上游测试。

## 计数依据

- `tests/test-triplet.sh`：12 行活动 `test` 调用；注释行不计数。
- `tests/test.sh`：逐一执行 `examples/` 的 18 个 `.acr` 文件。
- `test_package`：3 个场景，分别为版本查询、生成并执行 configure、缺失输入
  返回非零。Linux Python 测试含 6 个断言；PC 模拟器 shell 测试含 7 个断言。

## 前后结果

### 未修改上游

```text
source_sha256=18c8e66c297bb8216a6de54945701e6813f404e162887456f495a01bc1b427b3
BEFORE inventory=12+18 total=30
BEFORE triplets_rc=0 fail_markers=1
  OS FAIL   - coff vs linux
BEFORE examples_rc=0 executed=18/18
OK: All tests has passed fine
```

### 应用路径 B 补丁后

```text
AFTER inventory=12+18 total=30
AFTER triplets_rc=0 fail_markers=0
AFTER examples_rc=0 executed=18/18
OK: All tests has passed fine
config.sub_rc=0 config.sub=m68k-unknown-coff
```

## Conan 结果

- Linux x86_64 / GCC 14 / Release：通过；上游 30/30，`test_package` 通过。
- Linux x86_64 / GCC 14 / Debug：通过；上游 30/30，`test_package` 通过。
- OHOS 6.0 / armv8 / Clang 15 / Release：配方创建与打包通过。
- 产物：6 个命令脚本、3 个 ACR 模块、7 个 man page、GPL-2.0 license。
- ELF 与动态依赖：不适用；ACR 是架构无关 shell application，没有 ELF 产物。

## HarmonyOS PC 模拟器

目标：`127.0.0.1:5555`

```text
PASS 1/7: packaged acr script exists
PASS 2/7: acr -v returned zero
PASS 3/7: version is 2.2.6
PASS 4/7: configure generation returned zero
PASS 5/7: configure file exists
PASS 6/7: generated configure returned zero
PASS 7/7: missing-input fault injection failed as expected
RESULT: 7/7 assertions passed
```

测试同时扫描 `generate.log` 与 `configure.log`；未发现 `inaccessible or not
found`、`arithmetic expression` 或 `FAIL`。

## 结论与边界

路径 B 测试修复没有减少用例或降低断言强度，所有 30 个上游测试均执行并
通过。核心 ACR 工作流已在 HarmonyOS PC 模拟器实测通过。可选指令需要的
外部编译器、解释器或工具仍由 ACR 按上游语义检查，不在本任务中伪造。
