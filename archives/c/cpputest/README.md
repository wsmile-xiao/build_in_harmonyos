# CppUTest

CppUTest 是一个 C/C++ 单元测试框架, 设计简洁, 适合嵌入式系统开发。它支持测试桩 (mock)、内存泄漏检测和 C/C++ 双语言测试。

## 功能概述
- C 和 C++ 双语言单元测试支持
- 内存泄漏检测 (MEMORY_LEAK_DETECTION)
- 测试桩扩展 (CppUTestExt)
- 丰富的断言宏: CHECK, CHECK_EQUAL, STRCMP_EQUAL 等
- 命令行测试运行器 (CommandLineTestRunner)
- 测试分组 (TEST_GROUP) 和测试用例 (TEST)
- 无第三方依赖, 仅需 CMake
- 适合嵌入式系统和 TDD 开发

## OHOS 适配
- C/C++ 单元测试框架, 无第三方依赖, 构建简单
- CMake 构建为静态库, 生成 CppUTest + CppUTestExt 两个库
- 需设置 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64` (OHOS 平台适配)
- 支持内存泄漏检测和测试桩扩展

## 依赖关系
- **编译依赖**: 无
- **运行依赖**: 无

## 参考资料
- 官网: https://github.com/cpputest/cpputest
- 文档: https://cpputest.github.io/manual.html
