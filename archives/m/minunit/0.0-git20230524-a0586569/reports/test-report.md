# minunit 原生目标验证

官方源提交：a0586569bd8abfb7a37390d670484c201e9173bf。
原始源包 SHA-256：144c2518446032b1181b7656e9ddeba0c51337afa6b32401bc05c4f30d873a6e。

不可变目标事务 minunit-20261004-r001 的冻结 validator 为 PASS，唯一
launch=1，owned_processes=0，release/postrelease 完成。该官方回归入口
1/1 通过；其 11 个示例测试中 5 个成功、6 个精确预期失败，原官方脚本
与失败身份检查全部吻合。用例语义计数为 11/11，不把预期负例当跳过。

使用安装头文件的消费者为 2/2，真实 HarmonyOS/aarch64 计时后端专项
为 1/1（4 项断言），不将断言数与测试数混用。

`w3-report-binding.json`、`upstream-test.log`、`w3-consumer.stdout` 和
`harmony-test.log` 绑定原始 snapshot SHA-256：
f8134b430dfd1a48692aa7d2f5c2e09c917cf7027fcefa3f043f13a26c4bd63c。
这些文件是原始运行证据的派生展示，不表示重新执行了旧事务。

本轮配方补齐标准 export_sources 与空补丁集合应用入口，不更改上游头文件
或目标测试源码。完整原生 Conan/finish 以及修复后的平台 CI、AI Review
仍需独立完成；本报告不声称它们已通过或本 PR 已提审。
