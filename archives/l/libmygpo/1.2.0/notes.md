# 1.2.0 适配记录

从 Debian 权威 orig 源码完整构建，Qt 5.15.19 OHOS 原生 binary 可下载，未在下游偷偷编译 Qt。原生 moc 真实参与全部生成。

配方在 source() 中加入 QDateTime 直接 include，修复旧的传递头依赖；修正 native CMake 安装配置的 include 路径与 Qt5 Core/Network 依赖；消费者使用上游导出的 Mygpo-qt5/config/target。未删除生产 API、未添加空壳实现。

上游为 32 个 UrlBuilderTest 方法及 5 个 JsonCreatorTest 方法，共 37，不按两个程序或 init/cleanup 计数。两个原有 JSON 用例的日期 fixture 明确 UTC，期望字符串分别遵循显式 ISODate 与 QVariant JSON 的实际格式；全部测试方法、严格断言仍保留。r3 35/37 的失败被保留，r4 37/37 但安装消费者 CMake 配置失败也如实保留。

r5 修复消费者 Qt 原生 CMake 绑定后，Conan create RC0、37/37 上游、6/6 消费者，完整事务 PASS。可复用知识草稿 E8288；正式 finish/合同及 worker CI 仍未完成，尚未发布。
