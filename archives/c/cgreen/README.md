# cgreen

cgreen 是一个轻量级的 C/C++ 单元测试与 mock 框架。

## 功能概述

- C 与 C++ 双语言单元测试（同一 libcgreen 库）
- Describe/Ensure 风格与经典 Test/Suite 宏
- 断言约束（整数/字符串/指针/浮点）、BeforeEach/AfterEach 夹具
- mock 对象支持、参数化与反射 runner
- 文本 / cute / CDash 报告器（XML 报告器在 OHOS 不可用，见下）

## OHOS 适配

- 上游 1.6.4 为 CMake 项目，使用 CMake recipe 适配（CMAKE_SYSTEM_NAME=Linux）
- 构建期默认执行上游框架自测套件（断言/mock/runner/输出比对），26/26 通过
- `test_package` 用 cgreen 自身编写 4 个消费者程序（17 函数/44 断言）验证打包产物
- xml 报告器（create_xml_reporter）在 OHOS 上触发 SIGABRT，构建关闭
  CGREEN_WITH_XML（详见版本目录 notes.md）

## 依赖关系

- 无运行期依赖（仅系统线程库）

## 参考资料

- 官网: https://cgreen-devs.github.io/cgreen/
