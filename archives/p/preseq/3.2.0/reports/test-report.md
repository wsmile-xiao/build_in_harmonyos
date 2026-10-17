# preseq 3.2.0 测试报告

测试日期：2026-10-01；目标：HarmonyOS PC aarch64；W3 事务：`preseq-w3-20260930T160025Z`。

| 类型 | 发现/执行 | 结果 |
| --- | ---: | --- |
| 上游 Automake 注册测试 | 0/0 | 源码无 `TESTS`、`check_PROGRAMS` |
| 上游 README 示例 | 4/4 | mapped、BAM、histogram、coverage 均生成非空输出 |
| 安装后消费者测试 | 1/1 | 直方图外推表头和数据行断言成功 |

上游用例未修改。README 中不存在的 `*_read.txt` 路径仅在调用中改为发布包实际的 `*_hist.txt`，数据文件字节保持上游原样。目标机运行收据 12/12，`W3_PASS`；日志 SHA-256：`a6c6a29cc83dea3afcb29f9d3222f71ae1267f7261c4e193d675fd5cec4de6c8`。
