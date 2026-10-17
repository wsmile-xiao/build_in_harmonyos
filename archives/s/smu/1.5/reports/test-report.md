# smu 1.5：HarmonyOS PC 包内功能测试

测试日期：2026-09-23。目标为 H1 HarmonyOS PC（aarch64，
HongMeng Kernel 1.12.0）。测试对象是本次 `conan create` 创建的
`smu/1.5` 包内 `bin/smu`，由 Conan `test_package.test()` 实际调用。

| 测试类型 | 总数 | 通过 | 失败 | 跳过 |
|---|---:|---:|---:|---:|
| 上游自动测试 | 0 | 0 | 0 | 0 |
| 补充消费者功能测试 | 32 | 32 | 0 | 0 |

上游 v1.5 归档没有 `test`/`check` 目标或自动测试套件；`testdoc` 仅是
样例输入，没有随附固定预期。没有删除、改写或跳过上游自动测试。
补充测试覆盖 Markdown 到 HTML 的标题、强调、列表、链接、转义、
UTF-8、文件与 stdin、空输入、多缓冲区输入及命令行错误路径。
每例检查退出状态、stdout 和 stderr，共 96 项比较；OHOS 上按字节比较，
不归一化换行。`-v`、`-h` 与非法选项返回 1 且写 stderr，测试按上游
原有契约接受，不把合法的非零状态记为失败。

H1 原始 Conan 输出显示 `test_package` 的
`test()` 调用了包目录中的可执行文件，最后记录 `32 passed, 0 failed`；
原始 [32 项汇总](h1-functional-summary.json)记录
`system=HarmonyOS`、`machine=aarch64`、`status=passed`，每项结果均通过。
逐项对比实际与固定预期 stdout/stderr 文件，0 缺失、0 不符。
测试 runner SHA-256 为
`24ff9b62b124bf7072615dbb35fe3bd743f73e881b7a4979d3697391d3cf47cd`。

本报告的 32 项汇总对应 2026-09-23 单文件 OHOS profile 包内测试。
2026-09-24 的隔离框架 `finish` 内 G2 和 W3 也分别从源码建包、运行同一
32 项消费者测试并通过；W3 标记有效。`finish` 后续知识图谱/submit 就绪
检查未完整通过，官方 CI 尚未执行。框架 `conan-verify` 的 G4 找不到包 ID
却标 PASS，L2/L4/L5 无 cache 路径而跳过，不能据其标签声称全部门禁通过。
