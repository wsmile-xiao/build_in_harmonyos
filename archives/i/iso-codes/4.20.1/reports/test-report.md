# iso-codes 4.20.1 测试报告

> **测试日期**：2026-09-04  
> **构建目标**：OpenHarmony PC aarch64 (`os=OHOS`, `arch=armv8`)  
> **包引用**：`iso-codes/4.20.1#6e46398db2baf12833bd80cdfca21852:6b129b068851896169fae42d399fa922d239ce8a#79b0b192c662191dd40cde6a0fdb926d`

## 测试摘要

| 测试集合 | 用例 | 结果 | 补充计数 |
|----------|-----:|------|----------|
| 上游 Meson UTF-8 数据域测试 | 8/8 | PASS | 8 个声明数据域全部执行 |
| Conan 安装树消费者测试 | 1/1 | PASS | 1513/1513 断言通过 |
| 真机 W3 同一冻结测试闭包 | 9/9 | PASS | 上游 8 项及消费者 1 项，无新增分母 |

唯一测试用例数为 9，全部通过；消费者内部的 1513 项检查是断言数，不重复计作
1513 个测试用例。

## 上游测试清单

清单来自根 `meson.build` 的八个 `domains` 条目及每个域目录中的唯一
`test()`。构建入口执行：

```text
meson test -C <build_folder> --print-errorlogs --no-rebuild
```

不可变 r6 原始日志 SHA-256：
`547089826c2cfac094a6441825cafbf90c3147cec544fb2d894764b4a4ad53bd`。
原始日志报告 `Ok: 8`、`Fail: 0`；合同规范化读回在严格验证该日志后输出
`8/8 PASS`，不修改原始日志。

## 消费者与目标验证

消费者解析 8 个 JSON 数据文件、8 个 schema、8 个生成 XML，逐域比对 JSON
与 XML 记录数，验证 5 个 XML 兼容链接、`iso-codes.pc`、708 个 canonical
`.mo` catalog 及其 magic。Conan r6 输出
`ISO_CODES_VALIDATION_PASS assertions=1513`。

真机事务 `iso-codes-4.20.1-w3-r1` 在 `10.62.150.125:8022` 唯一启动一次，
`launch_count=1`，终态为 PASS；release/postrelease 回读确认 runner 与任务远端
根均不存在。终态 receipt SHA-256：
`8c7c641db2e0a021d4e3fd4f2414168ffeb513611fd9c26f9b30e70790436ee4`。

## 已知边界

该包是架构无关数据包，真机验证覆盖安装树语义和文件系统行为，不代表平台 CI。
提审必须等待 PR 当前 HEAD 的平台 AI Review 完成且平台 CI 明确 PASS。
