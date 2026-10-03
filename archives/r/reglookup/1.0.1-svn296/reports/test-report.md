# reglookup 1.0.1-svn296 测试报告

测试日期：2026-10-01；目标：HarmonyOS PC aarch64。

| 类型 | 发现/执行 | 结果 |
| --- | ---: | --- |
| 上游注册测试 | 0/0 | 发布包没有测试目标或样本 hive |
| 安装后 C API 消费者 | 1/1 | `range_list` 八项断言通过 |
| 真实 Windows hive 端到端解析 | 0 | 未提供测试 hive，不能声称通过 |

上游源文件没有修改。最终真机事务 `reglookup-w3-20260930T173100Z` 返回 `W3_PASS`，12/12 收据；日志 SHA-256 `0cc993be2da4481a54804ce261e3087dab39e856ed2300802038aabd31f5d673`。
