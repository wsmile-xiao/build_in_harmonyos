# unittestpp（UnitTest++）

UnitTest++ 是一个轻量级 C++ 单元测试框架（上游 unittest-cpp 项目，MIT），
单静态库 + 一组公共头文件，无外部依赖，适合在嵌入式/交叉编译场景下使用。

## 功能概述

- 断言宏：`CHECK` / `CHECK_EQUAL` / `CHECK_CLOSE` / `CHECK_ARRAY_*` /
  `CHECK_THROW` / `REQUIRE`（required check，失败即中止当前用例）
- 测试组织：`TEST` / `TEST_FIXTURE`（夹具）/ `SUITE`（套件）/ `UNITTEST_TIME_CONSTRAINT`
- 报告器：标准输出报告器（TestReporterStdout）、XML 报告器（XmlTestReporter）、
  延迟报告器（DeferredTestReporter）与自定义报告器接口（TestReporter）
- 平台支持：POSIX 平台层（`gettimeofday`/`usleep` 计时；`sigsetjmp`/`sigaction`
  信号翻译，把测试内的崩溃翻译为测试失败而非中止整个测试进程）

## OHOS 适配

- **零源码补丁**：上游 v2.0.0 用 OHOS SDK clang 15（aarch64-unknown-linux-ohos）
  直接编译通过；`Config.h` 依据三元组宏自动选中 `Posix/` 平台层。
- 唯一构建要求：CMake 4.x 下需 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`
  放行上游 `cmake_minimum_required(VERSION 2.8.1)`（recipe 已内置，无需人工干预）。
- 上游测试套件（21 个测试源文件，源码清点 277 用例）在 OHOS aarch64 真机原样运行：
  Release 构建实测 268/268、默认配置 267/267 全过（差异为上游条件编译分支）；
  Posix 信号翻译路径经消费者反向对照实测（`raise(SIGSEGV)` → 测试失败）。
- 已知平台注意点：本设备上「执行空指针函数调用」的硬件指令中止会让进程挂起，
  不适用作崩溃注入手段（`raise(SIGSEGV)`/空指针数据访问/`__builtin_trap` 正常）。

## 依赖关系

- 编译依赖：无（仅 C++ 标准库 + libc）
- 运行依赖：无（静态库）

## 使用方式（Conan）

```ini
[requires]
unittestpp/2.0.0
```

```cmake
find_package(UnitTest++ REQUIRED)
target_link_libraries(my_tests PRIVATE UnitTest++)
```

## 参考资料

- 源码仓库: https://github.com/unittest-cpp/unittest-cpp
- 版本: v2.0.0（2017-01-13，MIT）
