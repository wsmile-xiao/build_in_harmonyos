# CxxTest

CxxTest 是一个轻量级的 C++ 单元测试框架（header-only），风格类似 JUnit/CppUnit。它不需要预编译测试库、不依赖 RTTI 等高级 C++ 特性，通过 Python 驱动脚本 cxxtestgen 在构建期做测试发现并生成测试运行器。许可证为 LGPL-2.1。

## 功能概述
- 纯头文件框架：cxxtest/ 头文件集即"库"，测试代码直接 #include
- cxxtestgen（Python 3）构建期生成测试运行器：扫描 TestSuite 派生类，产出含 main() 的 runner 源码
- 丰富的断言宏：TS_ASSERT / TS_ASSERT_EQUALS / TS_ASSERT_DELTA / TS_ASSERT_THROWS / TS_ASSERT_SAME_DATA / TSM_* 变体等
- 多种运行器：ErrorPrinter / StdioPrinter / YesNoRunner / XML 输出
- 全局夹具（GlobalFixture）、Mock 支持（cxxtest/Mock.h）
- 无 RTTI 依赖、无预编译库，适合嵌入式与交叉编译场景
- 目标机不需要 Python：生成只发生在构建期

## OHOS 适配
- header-library 包类型：package_id clear（不依赖 os/compiler/build_type）
- 包内容：include/cxxtest/（头文件集 + Root.cpp 等源片段）+ res/cxxtest/（Python 3 驱动包）
- 消费者集成：`python3 <res>/cxxtest/cxxtestgen.py --error-printer -o runner.cpp suite.h` 生成 runner 后对 CxxTest::CxxTest 目标编译
- 生成的测试二进制在 OHOS 上运行需签名（E077）并带 SDK libc++ 的 LD_LIBRARY_PATH
- 上游 PyUnit 自测套件（TestClang 类）在设备上实测 60 用例 59 过 1 自跳（int64 用例依赖 MSVC 专有 `__int64` 类型，clang 探针失败自跳）

## 依赖关系
- **编译依赖**: 无
- **运行依赖**: 无（Python 仅构建期需要）

## 参考资料
- 官网: https://github.com/CxxTest/cxxtest
- 用户指南: doc/guide.pdf（源码包内）
