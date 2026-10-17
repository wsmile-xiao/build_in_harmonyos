# scrm

scrm 是顺序溯祖模型的命令行重组模拟器，输出兼容 ms 的序列、树和统计信息。

## HarmonyOS PC

Conan CMakeToolchain/CMakeDeps 构建原始 C++ 源码，避免上游写死的 `/opt/local/lib`。单元测试使用 `UNITTEST` 及调试实现，不能与生产对象混用；算法测试使用原生产核心。断言、种子和采样次数不变。

无第三方生产库依赖。完整测试需要已发布的 `cppunit/1.15.1` OHOS 二进制，不随 CLI 运行部署。软件类型 application，提供 `commands.json`。

官网：https://scrm.github.io；源码：https://github.com/scrm/scrm。
