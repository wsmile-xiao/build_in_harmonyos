# CppUTest

## 简介
CppUTest 是轻量级 xUnit 风格 C/C++ 单元测试框架，提供 TEST 宏、内存泄漏检测（可选）与扩展库（Mock/命令行驱动）。

## OHOS 适配
- 纯标准库 C++ 实现，静态库（libCppUTest.a / libCppUTestExt.a）
- 上游自有测试套件（TESTS=ON）随构建执行并逐用例注册 ctest
- 供 weechat 等项目在构建期链接使用（构建期依赖，不进入下游运行时）

## 依赖
- 无
