# utimer 0.4 测试报告

平台：HarmonyOS PC 6.0 / aarch64 / Clang 15.0.4。日期：2026-10-11。

## 上游测试

未修改 src/tests/maintests.c，执行 `utimer-upstream-tests --verbose -m slow`：5/5，100%。

| 注册用例 | 结果 |
| --- | --- |
| /Utils/Suffix/Test1 | PASS |
| /Timer/Duration/Test1 | PASS |
| /General/TimerCreation/Timer | PASS |
| /General/TimerCreation/Stopwatch | PASS |
| /General/TimerCreation/Countdown | PASS |

## 新增消费者

安装版本、安装帮助、有限 timer EOF、有限 countdown EOF、stdin 保持打开的有限 timer、limits、缺失参数拒绝、未知参数拒绝：8/8。有限计时要求实际耗时不少于 0.08 秒且小于 5 秒，单项超时 8 秒；不是仅检查日志字符串，也不会向进程发送 quit 来伪造自然退出。

## 证据与边界

当前独立事务 `utimer-full-finish-r2-20261011T094000Z`：一次 launch，12 个 phase、release/postrelease 均 PASS。日志 SHA256 `01d7865ff4b3b5654a79635230e1b9717d1c6dd8922a7b4ddf776fb2683a2602`；官方 CI 安装 ELF SHA256 `5f1df01b04cd1aa523fc0ac5af33bc63e13c9441866b37cbff3c64a2cb2c1bd1`。

完整官方 FinishPipeline 实际执行；正式 Conan 验证与官方 W3 子步骤通过。L1e 移走安装 bin 后消费者确实失败。官方 L2 非阻塞 SKIP，ConanVerifier 的 L2/L4/L5 因 cacheID 解析限制 SKIP，不能替换为执行 PASS。整体 finish RC1 / PARTIAL_POST_W3，仅 step5b/step8 的旧知识及归档元数据检查失败；不修改框架、不人工补造 .ci-result.json。该文件原始 SHA256 `83b12d7f39d0e2c5550d4a37f7ea681c31b0195f13ab684895c55b100f2a5737`，时间戳 `2026-10-11T17:33:17.719022`，integrity `36894f269bb0195b`。尚无比赛 worker CI、平台 AI Review 通过或制品发布结论。
