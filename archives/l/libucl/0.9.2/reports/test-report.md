# libucl 0.9.2 测试报告

## 上游测试范围

上游 `tests/Makefile.am` 的 `TESTS` 注册 5 个唯一 `make check` 套件：`basic.test`、`generate.test`、`schema.test`、`msgpack.test` 和 `speed.test`（`msgpack.test` 在原列表中重复声明一次）。`streamline.test` 是源码树中的额外上游脚本，但未由 `make check` 注册，因此单独记录，不计入注册套件数。

按数据驱动输入统计，注册的 `make check` 范围覆盖 50 个测试数据项：basic 22 项、generate 1 项、schema 25 项、msgpack 1 项、speed 1 项。额外的 `streamline.test` 覆盖 1 项。`basic.test` 还为每个输入执行 FD、JSON、紧凑 JSON、YAML、保存注释和保存宏输出模式。

## 执行结果

| 上游测试套件 | 数据项 | 原始上游脚本结果 | 功能验证结果 | 备注 |
|---|---:|---|---|---|
| `basic.test` | 22 | PASS | PASS | 22 个输入及附加输出模式均成功。 |
| `generate.test` | 1 | PASS | PASS | 生成结果与 `generate.res` 一致。 |
| `schema.test` | 25 | FAIL | PASS (25/25) | 原始脚本硬编码写 `/tmp/_ucl_test_schema.out`，鸿蒙 `/tmp` 只读；逐个调用同一 `test_schema` 二进制验证 25 个 schema 全部成功。 |
| `msgpack.test` | 1 | PASS | PASS | 上游 MessagePack 测试程序成功。 |
| `speed.test` | 1 | PASS | PASS | 成功解压并解析 `rcl_test.json.xz`。 |
| `streamline.test` | 1 | FAIL | PASS | 上游程序仅在 `argc == 2` 时使用输出路径，而脚本传一个参数；标准输出内容与 `streamline.res` 完全一致。 |
| **注册 make-check 合计** | **50** | **4/5 套件脚本通过** | **50/50 数据项功能通过** | `schema.test` 原脚本受只读 `/tmp` 限制，等价输入验证 25/25 通过。 |
| **含额外 streamline 脚本合计** | **51** | **4/5 注册套件通过；额外脚本失败** | **51/51 数据项功能通过** | `streamline.test` 未被 `make check` 注册；其标准输出与基线一致。 |

## Conan 消费者测试

`test_package/test.c` 通过 `ucl::ucl` 解析 `answer = 42; enabled = true;`，并验证整数和布尔值的 typed lookup。官方定向 CI 结果：`test_libucl` 1/1 PASS；L1e 破坏性反向验证确认测试实质依赖被测库。
