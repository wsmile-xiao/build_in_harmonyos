# inih/r62 — 私有真机测试报告

- 授权目标：HarmonyOS PC 真机；全新私有根 a679。
- 输入：官方 r62 tar.gz，22,145 字节、SHA-256 `9c15fa751bb8093d042dae1b9f125eb45198c32c6704cd5481ccde460d4f8151`；候选代码与归档均独立完整回读。
- 命令：隔离 `CONAN_HOME`、可写 `TMPDIR`、目标 OHOS 6.0 Clang/llvm-ar profile 下 `conan create`。
- 结果：RC0；原始上游 15/15 配置执行，输出与官方 baseline 逐字节相同；已安装包消费者 3/3。
- 原始日志：D 盘任务目录 `a679-create.log`，20,619 字节，SHA-256 `b98068b71b2d70eae5d33c16b9b6886e4eced4972ab165ae70604d02efc48939`。
- 来源边界：设备未直连 GitHub；Conan 从目标私有固定 SHA 缓存取回官方归档。
- 流程边界：探索性真机证据，非正式 W3、平台 CI 或积分。
