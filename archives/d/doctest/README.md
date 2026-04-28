# doctest

doctest 是一个 C++ 单元测试框架，特点是编译速度快，API 设计灵感来自 Python 的 doctest 模块。

## 功能概述
- 极快的编译速度（相比 Google Test/Catch2）
- API 简洁，类似 Python doctest
- Header-only 模式可选
- 支持子过程、测试套件、BDD 风格
- 线程安全

## OHOS 适配
- Header-only 库，编译非常简单
- CMake 构建，无需特殊适配
- 无需补丁即可在 HarmonyOS 上编译

## 依赖关系
- **编译依赖**: 无（header-only）
- **运行依赖**: 无

## 参考资料
- 官网: https://github.com/doctest/doctest
- 文档: https://github.com/doctest/doctest/blob/master/doc/markdown/readme.md
