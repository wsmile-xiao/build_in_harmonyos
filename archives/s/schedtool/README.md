# schedtool

schedtool 是查询和设置进程调度策略、静态优先级、nice 值与 CPU 亲和性的命令行工具。上游版本为 1.3.0，许可证 GPL-2.0-only。

上游：https://github.com/freequaos/schedtool

本次配方为原生构建，目标为 OHOS aarch64。系统运行库之外没有第三方链接依赖；构建需要 C 编译器、GNU Make，消费者测试需要提供调度查询 API 的 Python 3。

1.3.0 已在 HarmonyOS aarch64 真机完成原生构建、独立功能测试及 Conan 从上游源码创建包和包内测试，直接与包内测试均为 18/18、103 断言；正式 W3 本地 CI 亦通过，证据范围和限制见 `1.3.0/reports/`。完整 `finish` 后续收尾与官方 CI 尚未通过，当前不宣称已发布。各调度策略的可用性和权限受目标内核限制，`-r` 只能查询优先级范围，不证明能设置该策略；实时策略未纳入普通回归测试。
