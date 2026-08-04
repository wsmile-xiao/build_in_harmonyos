# cmocka

cmocka 是一个优雅的 C 语言单元测试框架，支持 mock 对象。

## 功能概述

- C 语言单元测试框架
- 支持 mock 对象和函数
- 支持 setup/teardown
- 内存泄漏检测
- 多种输出格式

## OHOS 适配

- 上游 2.0.2 为 CMake/Meson 项目，当前使用 CMake recipe 适配
- 默认启用 examples 和 upstream unit tests，并在构建阶段执行全量 CTest
- `test_package` 编译并运行一个最小 cmocka 测试程序，验证 CMake target 和运行时

## 依赖关系

- C 编译器

## 参考资料

- 官网: https://cmocka.org/
