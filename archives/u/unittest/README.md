# unittest

David Carlton 编写的 xUnit 风格 C++ 单元测试框架：测试用例表示为类，
以构造函数/析构函数做 setup/teardown，通过 `UnitTest::Suite` 聚合、
`UnitTest::Registry` 运行，以 `ASSERT`/`ASSERT_EQUALS`/`ASSERT_EXCEPTION`
宏上报断言。

## 功能概述
- 头文件 + 单静态库（`libunittest.a`），零第三方依赖
- 断言宏：`ASSERT`、`ASSERT_EQUALS`、`ASSERT_EXCEPTION`、
  `ASSERT_EXCEPTION_MESSAGE`、`FAIL`
- 测试组织：`Suite::add<>()` 注册、`createSuite` 嵌套、`Registry` 运行
- 信号安全：sigaction/siglongjmp 捕获测试中的 SIGSEGV/SIGFPE/SIGABRT
  并记为用例失败而非进程崩溃
- 自带上游自检套件 `test/unittesttest`（6 套件 63 叶子用例）

## OHOS 适配
- 适配要点：纯 C++03（以 `-std=c++03` 编译，与 Homebrew 公式一致）；
  信号测试以 `raise()` 注入，与硬件 fault 语义无关，AArch64 一致；
  `execinfo.h` 缺失时 configure 自动降级（仅关闭崩溃栈回溯打印）
- 已知限制：上游只提供静态库（无共享库规则），`shared=True` 会被配方拒绝
- 与 Linux 的差异：预计无（待真机预检确认）

## 依赖关系
- 编译依赖：无（仅工具链自带的 C++ 标准库、POSIX 信号接口与 `cxxabi`）
- 运行依赖：无

## 参考资料
- 官网：https://unittest.red-bean.com/
- 源码浏览：http://viewvc.red-bean.com/unittest/trunk/
- Homebrew 公式（版本/sha256 交叉核对）：
  https://github.com/Homebrew/homebrew-core/blob/master/Formula/u/unittest.rb
