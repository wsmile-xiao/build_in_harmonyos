# limonp — C++ header-only 基础设施库（字符串 / 日志 / 配置 / 小容器）

## 概述

limonp（yanyiwu/limonp）是 cppjieba 作者从分词器工程里抽出来的 C++ 头文件库
（MIT）。它不追求通用，只做几件在"文本处理 + 命令行工具"场景里反复出现的事：

- **`limonp::StringUtil`**：`Split` / `Join` / `StringFormat` / `Trim` /
  `StartsWith` / `EndsWith` / `PathJoin` / `GetTime`，以及
  UTF-8 ↔ UTF-16、GBK ↔ UTF-16 的双向转换；
- **`limonp::Logging`**：`XLOG(DEBUG|INFO|WARNING|ERROR|FATAL)` 与 `XCHECK`，
  带时间戳的流式日志；
- **`limonp::Config`**：`key=value` 配置文件解析（支持注释与 `[...]` 段）；
- **`limonp::LocalVector<T>`**：栈上内联 16 个元素的小向量，溢出才上堆；
- **`limonp::Closure`**：`NewClosure()` 绑定自由函数/成员函数并延迟调用；
- **`limonp::ArgvContext`**：`--key value` / `-k v` / 位置参数的命令行解析；
- **`limonp::Colors`**：ANSI 彩色 stderr 输出。

**本仓库适配版本**：1.0.2（HarmonyOS PC aarch64）

## 功能概述

- `add_library(limonp INTERFACE)` —— 纯头文件，产物只有 `include/limonp/*.hpp`
  与上游 `install(EXPORT limonp)` 生成的 `limonp-config.cmake`，运行时零依赖
  （`Condition.hpp` 用到 `pthread_cond_*`，但上游 unit test 不引用它，
  消费者若要用需自行链接 `-pthread`）。
- 上游测试：顶层注册 2 个 ctest 用例（`./test/demo` 与 `./test/test.run`），
  其中 `test.run` 里是 25 个 gtest `TEST` 用例。

## OHOS 适配要点

1. **上游 unit test 在 configure 期联网**：`test/unittest/CMakeLists.txt` 用
   `FetchContent_Declare(googletest GIT_REPOSITORY ... GIT_TAG release-1.12.1)`
   + `FetchContent_MakeAvailable(googletest)` 在 configure 期 `git clone`。
   CI worker 不可联网。本包用 `test_requires("gtest/1.17.0.1")`（ohpcd 已发布：
   OHOS/armv8/clang15/libc++/cppstd17）+ patch 0002 换成
   `find_package(GTest REQUIRED)` / `GTest::gtest`。
   **`test.run` 自带 `main()`（`test/unittest/gtest_main.cpp`），所以只能链
   `GTest::gtest`，链 `GTest::gtest_main` 会 duplicate symbol。**
2. **上游测试的 fixture 是相对路径**：`TConfig.cpp` / `TStdExtension.cpp` /
   `TStringUtil.cpp` 用 `"../test/testdata/..."` 打开 fixture，而两个 `ADD_TEST`
   的 COMMAND 也是相对路径且没有 `WORKING_DIRECTORY` —— 只有 build 目录恰好是
   源码根的直接子目录时才成立（上游 CI 正是如此）。Conan 的 build 目录与
   source 目录互为**兄弟**节点，不打 patch 0001 会有 4 个用例因 fixture
   打不开而失败（实测 `50% tests passed, 1 tests failed out of 2`）。
3. **`char` 的默认有符号性在平台间不同**：aarch64-linux（含 OHOS）的 `char`
   是 **unsigned**，x86-linux 是 **signed**。GBK 的 `中` = 字节 `D6 D0`，
   `0xD6` 在 x86 的 `signed char` 里是 -42。`StringUtil.hpp:165` 的
   `TwocharToUint16` 用 `uint16_t(high) & 0x00ff`（先转无符号再掩码）保证两端
   都得到 `0xD6D0` —— 本包消费者测试把这条写成了一组鸿蒙特有断言。
4. **`IsSpace(unsigned)` 的越界守卫**：`StringUtil.hpp:83` 注释明说"把大整数
   喂给 `isspace` 会 core dump"，所以先用 `c > 0xff` 早退。`wchar_t` 在
   aarch64/OHOS 上是 4 字节（Windows 上 2 字节），`IsSpace(1000024u)` 必须
   被拦住而不是把 `1000024 & 0xff` 拿去查 ctype 表。
5. **编码转换不走平台 locale / iconv**：`GBKTrans` / `Utf8ToUnicode` 都是纯
   计算（字节对打包 / 位运算），OHOS/bionic 既没有 GBK locale 也没有 iconv，
   这条往返必须在 aarch64 上与 x86 逐位一致。

## 依赖关系

- 编译依赖：无（header-only）
- 测试依赖：`gtest/1.17.0.1`（`test_requires`，仅测试期）
- 运行依赖：无

## 打包产物

```
include/limonp/*.hpp
lib/cmake/limonp/limonp-config.cmake
licenses/LICENSE
```

> 上游的两个缺陷都由本包的 patch 修掉：patch 0002 把 configure 期联网的
> `FetchContent` 换成 Conan 的 GTest target，patch 0001 给两个 ctest 用例补上
> 显式 `WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}/test` 并把 COMMAND 换成
> `$<TARGET_FILE:...>`，让相对 fixture 路径在 out-of-tree 构建目录下也能解析。

## 参考链接

- 上游仓库：https://github.com/yanyiwu/limonp
- 本仓库版本笔记：`1.0.2/notes.md`
