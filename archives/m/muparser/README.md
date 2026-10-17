# muparser

muparser 是一个高性能 C++ 数学表达式解析库，支持函数、变量、常量、
二元/一元操作符、条件表达式与批量求值，广泛应用于科学计算与配置解析。

## 特性
- 纯 C++（C++20），零第三方依赖
- 表达式求值、变量/常量定义、自定义函数与操作符
- 批量求值（bulk mode）、本地化小数点
- 提供 C API（muParserDLL.h）

## OHOS 适配
- 构建系统: cmake
- 交叉编译: aarch64-unknown-linux-ohos clang 15（OHOS SDK 26.0.0.18）
- 上游测试: test/t_ParserTest.cpp (ParserTester)，604 个独立表达式断言全部通过
- 鸿蒙专项测试: 8/8 通过（uname 确认 HarmonyOS / HongMeng Kernel 1.12.0 / aarch64）
- conan-verify G0-G4 + L2/L4/L5 全部通过；消费者验证 (1+2)*3^2=27.0 运行成功

## 来源
- 官方仓库: https://github.com/beltoforion/muparser
- 版本: 2.3.5 (2024-12-13)
- 源码 SHA-256: 20b43cc68c655665db83711906f01b20c51909368973116dfc8d7b3c4ddb5dd4
