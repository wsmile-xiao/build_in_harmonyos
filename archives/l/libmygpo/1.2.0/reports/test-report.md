# 原生测试报告

目标：OHOS 6 arm64，Clang 15.0.4、Qt 5.15.19。

| 类型 | 上游原始分母 | 本次通过 | 说明 |
| --- | --- | --- | --- |
| UrlBuilderTest | 32 | 32 | 原方法全量；不计 init/cleanup |
| JsonCreatorTest | 5 | 5 | 原方法全量，UTC fixture/两种格式期望有修改 |
| 安装包消费者 | 不属于上游 | 6/6 | 真实调用已安装库：版本、user-agent、base URL、播客文本、计数及 URL |

run_id `libmygpo-w3-r5-20261011T183000Z`；Conan create RC0，完整 12 receipts、release/postrelease PASS。日志 SHA-256 `7582139e3c4616553185c15fb71e8f8418bcf0fcadef4c54a8d533ba7420ea4f`，terminal SHA-256 `3d7cd3626d0812aca50b4f4459405872932564e2247fe1b31a211173e04791df`。

正式完整收尾的新事务 `libmygpo-full-finish-20261011T101500Z` 已完成：ConanVerifier PASS、官方 step35 PASS，上游 37/37、消费者 6/6，独立 W3 12 个阶段及 release/postrelease PASS；只 launch 一次。

当前日志 SHA256 `b2f2d5e64a5357546d22d8513ad657ec7f39c7dfd804d41f86492495f8665620`；terminal SHA256 `562e8a8fa6c636beec10a4ab6e87ed325e3420e1ffe2f87cfe6dbf1bbfa2e1f0`；官方安装库 SHA256 `8284694c09c22843ebffb243a4dfcd3ac94277b62bbf50b24412bfd2b95a6f3a`。RREV `5dfb43b840e759f7ce70adf9026def09`。

完整 finish 整体 RC1 / PARTIAL_POST_W3，仅 step5b/step8 的既有知识字段和旧归档元数据约束失败。ConanVerifier L2/L4/L5 因 cache 路径解析限制 SKIP，不写成实际执行 PASS。原始 `.ci-result.json` SHA256 `97f262d3a03e91f9410fb525082f932eec1fbfa6ada7191ade30095cc5fa282e`，timestamp `2026-10-11T18:00:33.302477`，integrity `49199ad2b217d14d`；不人工改写、不修改框架。

这是目标机原生结果，不是比赛 worker CI，也不代表在线 gpodder API 端到端验收。
