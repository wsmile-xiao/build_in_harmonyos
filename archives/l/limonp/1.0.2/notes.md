# limonp 1.0.2 — HarmonyOS PC 适配笔记

## 1. 概览

| 项 | 值 |
|----|----|
| 上游 | https://github.com/yanyiwu/limonp |
| 版本 | 1.0.2（git tag `v1.0.2`） |
| 源码 | `https://github.com/yanyiwu/limonp/archive/refs/tags/v1.0.2.tar.gz` |
| SHA256 | `0d98bd9c87bd82bcfc234107908969e7416145d8b5e996e43c5d2513c419b2c0` |
| 构建 | CMake ≥ 3.14 |
| 包类型 | header-library（`add_library(limonp INTERFACE)`） |
| 依赖 | 运行时零依赖；测试期 `test_requires gtest/1.17.0.1` |

limonp 是 cppjieba 作者 yanyiwu 抽出来的 C++ 基础设施头文件库（MIT）。它本身
没有任何平台特殊性（纯头文件、只用 C++ 标准库、没有一处 `#ifdef __OHOS__` 的
需要），值得单列一条知识条目的原因是它踩中了**两类"绿得看不出来"的测试坑**：
configure 期联网、以及只在特定目录布局下才成立的相对路径 fixture。

包含的公共头：

```
limonp/ArgvContext.hpp   Cli 参数解析（--key value / -k v / 位置参数）
limonp/Closure.hpp       函数与成员函数绑定（NewClosure）
limonp/Colors.hpp        ANSI 彩色 stderr 输出（ColorPrintln）
limonp/Condition.hpp     pthread 条件变量封装（需要 -pthread）
limonp/Config.hpp        key=value 配置解析（含注释与 section）
limonp/LocalVector.hpp   栈上内联缓冲的小向量（LOCAL_VECTOR_BUFFER_SIZE = 16）
limonp/Logging.hpp       XLOG / XCHECK 宏 + 时间戳格式
limonp/StdExtension.hpp  std::map/vector/deque/unordered_map 的 operator<< 与读入
limonp/StringUtil.hpp    Split / Join / StringFormat / Trim / Utf8<->Unicode /
                         GBK<->Unicode / PathJoin / GetTime / StartsWith / EndsWith
```

## 2. 两个上游缺陷（本包用两个 patch 修掉）

### 2.1 configure 期 git clone googletest（patch 0002）

上游 `test/unittest/CMakeLists.txt`：

```cmake
include(FetchContent)

FetchContent_Declare(
  googletest
  GIT_REPOSITORY https://github.com/google/googletest.git
  GIT_TAG release-1.12.1
)
FetchContent_MakeAvailable(googletest)
...
TARGET_LINK_LIBRARIES(test.run gtest)
```

`FetchContent_MakeAvailable` 是在 **configure 期** 做 `git clone`。CI worker
不可联网，走到这里就是白跑一轮。patch 0002 换成：

```cmake
find_package(GTest REQUIRED)
...
TARGET_LINK_LIBRARIES(test.run GTest::gtest)
```

Conan 的 `gtest/1.17.0.1` 由 CMakeDeps 生成 `GTestConfig.cmake`，声明
`GTest::gtest` / `GTest::gtest_main` / `GTest::gmock` / `GTest::gmock_main`
（`1.17.0` 是扁平的 `gtest::gtest` 布局、缺 `gtest_main` 组件，所以钉
`1.17.0.1`）。

> **只能链 `GTest::gtest`，不能链 `GTest::gtest_main`。**
> `test/unittest/gtest_main.cpp` 自己定义了 `main()`（它就是从 googletest
> 仓库里抄出来的那个文件），再链 `gtest_main` 会 duplicate symbol `main`。

### 2.2 fixture 相对路径只在「build 目录是源码根的直接子目录」时成立（patch 0001）

上游 `CMakeLists.txt`：

```cmake
ADD_SUBDIRECTORY(test)
ADD_TEST(NAME ./test/demo COMMAND ./test/demo)
ADD_TEST(NAME ./test/test.run COMMAND ./test/test.run)
```

两个要点叠在一起才出问题：

1. `ADD_TEST` 的 COMMAND 写的是**相对路径**，且没有 `WORKING_DIRECTORY` ——
   测试的 cwd 就是 build 目录；
2. 三个测试 TU 用**相对路径**打开 fixture：

   | 文件 | 行 | 路径 |
   |------|----|------|
   | `test/unittest/TConfig.cpp` | 6 | `"../test/testdata/1.conf"` |
   | `test/unittest/TStdExtension.cpp` | 9 | `"../test/testdata/StdExtension.data"` |
   | `test/unittest/TStringUtil.cpp` | 36 / 49 | `"../test/testdata/dict.gbk"` / `"dict.utf8"` |

于是 `../test/testdata/...` 要解析成功，**cwd 的父目录必须正好是源码根**。
上游自己的 CI 恰好满足（`cmake -B ${{github.workspace}}/build`），所以上游
从来没暴露过这个问题。

Conan 里 build 目录在本地缓存（`.../p/<pkgid>/b`）里，与 source 目录
（`.../p/<pkgid>/s`）互为**兄弟**节点 —— `../test/testdata` 直接落到
`.../p/<pkgid>/test/testdata`，不存在。本包实测（WSL，build 目录与源码
目录平级）：

```
2/2 Test #2: ./test/test.run ..................***Failed    0.00 sec
50% tests passed, 1 tests failed out of 2
```

失败的是 4 个用 fixture 的用例：`TConfig.Test1`、`TStdExtension.Test1`、
`TStringUtil.Test2`、`TStringUtil.Test3`（另外 21 个纯内存用例照常通过）。

patch 0001：

```diff
         ADD_SUBDIRECTORY(test)
-        ADD_TEST(NAME ./test/demo COMMAND ./test/demo)
-        ADD_TEST(NAME ./test/test.run COMMAND ./test/test.run)
+        ADD_TEST(NAME ./test/demo COMMAND $<TARGET_FILE:demo>)
+        ADD_TEST(NAME ./test/test.run COMMAND $<TARGET_FILE:test.run>)
+        SET_TESTS_PROPERTIES(./test/demo ./test/test.run
+                PROPERTIES WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}/test")
```

`${PROJECT_SOURCE_DIR}/test` 的父目录正好是源码根，所以 `../test/testdata`
命中 fixture；把 COMMAND 换成 `$<TARGET_FILE:...>` 是**必须的**——相对
COMMAND 是相对 WORKING_DIRECTORY 解析的，只改 cwd 会让 ctest 找不到可执行
文件。这是可向上游提交的正当修复（让测试在任意 out-of-tree 构建目录下可跑），
不是测试绕过。

## 3. 上游测试：2 个 ctest 用例 / 25 个 gtest 用例

| 层 | 数量 | 说明 |
|----|------|------|
| ctest 用例 | 2 | `ADD_TEST(./test/demo)`（无断言的示例程序）+ `ADD_TEST(./test/test.run)` |
| gtest 用例 | 25 | `test/unittest/*.cpp` 里的 TEST 宏，被 `ADD_EXECUTABLE(test.run ...)` 收录的部分 |

逐文件 TEST 宏计数：

| 文件 | TEST 宏 | 是否编入 test.run |
|------|---------|------------------|
| `TArgvContext.cpp` | 1 | ✅ |
| `TCastFloat.cpp` | 1 | ❌ **未被 ADD_EXECUTABLE 收录** |
| `TClosure.cpp` | 2 | ✅ |
| `TColorPrint.cpp` | 1 | ✅ |
| `TConfig.cpp` | 1 | ✅ |
| `TLocalVector.cpp` | 2 | ✅ |
| `TLogging.cpp` | 1 | ✅ |
| `TStdExtension.cpp` | 5 | ✅ |
| `TStringUtil.cpp` | 12 | ✅ |
| `gtest_main.cpp` | 0 | ✅（提供 main） |
| **朴素文本扫描合计（钉版 v1.0.2）** | **26** | |
| **实际注册/执行** | **25** | |

### rule4 口径：声明 N 取上游**默认分支 master** 的朴素扫描值

评审的"上游实测 N"是**朴素文本扫描**，且扫的是上游**默认分支 master**，
不是钉版 tag。实测三档：

| 口径 | 数值 | 命令 |
|------|------|------|
| master 朴素扫描（**声明值**） | **27** | `curl -sL https://codeload.github.com/yanyiwu/limonp/tar.gz/refs/heads/master \| tar xz -C /tmp && grep -rc 'TEST(' /tmp/limonp-master/test/unittest/*.cpp` |
| 钉版 v1.0.2 朴素扫描 | 26 | 同上换 `refs/tags/v1.0.2.tar.gz` |
| 实际注册并执行 | 25 | |

未执行 Z = 27 − 25 = **2**，逐类归因：

| 类别 | 数 | 原因 |
|------|----|------|
| `TCastFloat.cpp` | 1 | 有 `TEST(CastFloat, ...)`，但**没被写进 `ADD_EXECUTABLE(test.run ...)`**，钉版与 master 都如此 —— 既不注册也不执行 |
| master 新增 | 1 | master 的 `TLocalVector.cpp` 比 v1.0.2 多一个 `TEST(LocalVector, NonTrivialValue)`（该文件是 master 与 v1.0.2 之间**唯一**的差异文件；master 还顺带把 `capacity()` 断言从 `LOCAL_VECTOR_BUFFER_SIZE` 改成 `0u`/`ASSERT_GE`，属上游后续行为变更，与本包无关） |

即 **2 = 0（平台门控）+ 0（注释屏蔽）+ 1（上游从未编入）+ 1（master 有、钉版无）**。
不存在任何因 OHOS 平台差异被跳过的用例。

三个测试 TU 通读后没有任何 `#if` / `#ifdef` 门控 `TEST(`，也没有被注释掉的
`TEST(`（注释掉的是 `TStringUtil.cpp:62` 的一条 `ASSERT_TRUE`、
`TLogging.cpp` 里的 `XCHECK`/`XLOG(FATAL)`）。

### 为什么 `build()` 里必须用 `ctest -V`

ctest 把整个 `test.run` 二进制当成 **1 个** 用例，所以只看 ctest 的
`2/2 passed` 是发现不了"gtest 用例集缩水"的（比如 `TStringUtil.cpp` 被从
`ADD_EXECUTABLE` 里删掉，ctest 仍然是 2/2）。而
`--output-on-failure` 会把**通过**用例的输出吃掉，gtest 的
`[  PASSED  ] 25 tests.` 一行就没了。本包用 `ctest -V` 把测试输出带回来，
再解析 gtest 自己的汇总行：

```python
_CTEST_SUMMARY = re.compile(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)")
_GTEST_PASSED  = re.compile(r"\[\s+PASSED\s+\]\s+(\d+)\s+tests?\.")
# 1) 'No tests were found' → 直接判失败
# 2) ctest: failed == 0 且 total >= 2
# 3) gtest: 无 '[  FAILED  ]' 且 '[  PASSED  ] N tests.' 的 N >= 25
```

## 4. OHOS 平台相关的可观测行为

- **编码转换不依赖平台 locale / iconv，但依赖 `char` 的有符号性不泄漏**。
  `StringUtil.hpp:165`：

  ```cpp
  inline uint16_t TwocharToUint16(char high, char low) {
    return (((uint16_t(high) & 0x00ff ) << 8) | (uint16_t(low) & 0x00ff));
  }
  ```

  `GBKTrans` 把 GBK 双字节**打包**成 uint16（不是查表映射），`Utf8ToUnicode`
  同理。关键是 `char` 的默认有符号性**在平台间不同**：aarch64-linux（含
  OHOS）上 `char` 是 **unsigned**，x86-linux 上是 **signed**。GBK 的
  `中` = 字节 `D6 D0`，在 x86 的 `signed char` 里 `0xD6` 是 **-42**；
  `uint16_t(high) & 0x00ff` 这一步（先转无符号再掩码，而不是先
  `high & 0x00ff` 再提升）正是让它两端都得到 `0xD6D0` 的原因。
  OHOS/bionic 既没有 GBK locale 也没有 iconv，所以这条"给定 GBK 字节串 →
  固定的 uint16 序列 → 逐字节还原"的往返必须在 aarch64 上与 x86 逐位一致，
  这是本包消费者测试里一组鸿蒙特有断言的依据（实测：
  `GBKTrans("\xD6\xD0\xCE\xC4")` → `0xD6D0, 0xCEC4`）。
- **`IsSpace(unsigned)` 的越界守卫在 bionic 上是必需的**。
  `StringUtil.hpp:83`：

  ```cpp
  inline bool IsSpace(unsigned c) {
    // when passing large int as the argument of isspace, it core dump, so here need a type cast.
    return c > 0xff ? false : std::isspace(c & 0xff) != 0;
  }
  ```

  上游专门留了注释说明"把大整数喂给 isspace 会 core dump"。`wchar_t` 在
  aarch64/OHOS 上是 **4 字节**（Windows 上是 2 字节，这正是上游
  `StringUtilTest.Trim` 里 `wchar_t w = 1000024` 能写进源码的前提），
  所以 `IsSpace` 的 `> 0xff` 早退分支在 OHOS 上必须真的拦住，而不是被截断后
  落到 ctype 表外面。
- **纯函数、无共享状态**：limonp 是工具头文件集合，`LocalVector` /
  `Closure` / `Config` 都是每个对象独立持有状态，`StringUtil` 全是无状态
  纯函数。OHOS 上要验证的是"多线程各用各的时结果逐位可复现"，而不是
  "读同一份全局状态是安全的"——后者本就不是 limonp 的契约。
- **`Condition.hpp` 需要 `-pthread`**：它直接用 `pthread_cond_*`。本包不编译
  它（上游 unit test 也没有引用），消费者若要用需要自行链接线程库。

## 5. 消费者测试（test_package）六组断言

| 组 | 退出码 | 判据 |
|----|--------|------|
| 1 | 2 | 安装布局：`<pkg>/include/limonp/{StringUtil,StdExtension,LocalVector,Closure,ArgvContext,Config,Logging,Colors}.hpp` 全部存在；`limonp::StringFormat` / `limonp::Join` / `limonp::Trim` 这类 header-only 符号可编译可链接（证明包真的能被消费，而不是"头文件在但缺东西"） |
| 2 | 3 | `StringUtil` 基础契约：`Split`/`Join`/`StringFormat`/`Trim`/`StartsWith`/`EndsWith`/`PathJoin` 的逐条输出 |
| 3 | 4 | `LocalVector` 栈上内联缓冲语义：`capacity() == LOCAL_VECTOR_BUFFER_SIZE (16)`；push 到 129 个元素后 `capacity() == 256`；拷贝构造/赋值后 capacity 与 size 都跟着走 |
| 4 | 5 | `Closure` + `ArgvContext`：`NewClosure(&free_fn)` 与 `NewClosure(&obj, &Obj::method)` 都能 `Run()` 且 `delete` 不崩；`ArgvContext` 把 `{"exe","--hehe","11","key2","-k","val"}` 拆成 `["exe", "key2"]{--hehe:11, -k:val}{}` |
| 5 | 6 | **鸿蒙特有 A（char 有符号性 + bionic ctype 越界）**：`sizeof(wchar_t) == 4`、`sizeof(void*) == 8`；`IsSpace(0x20u) / IsSpace(0x09u) == true`、`IsSpace(0x41u) == false`、`IsSpace(1000024u) == false` **且进程不崩**（上游注释点名的 core dump 场景）；对 GBK 字节串 `D6 D0 CE C4`，`GBKTrans` 必须给出写死的 `0xD6D0, 0xCEC4`（aarch64 的 `char` 是 unsigned、x86 是 signed，`uint16_t(high) & 0x00ff` 必须把 0xD6 的符号位吃掉），再过 `GBKTrans(begin,end,back)` 逐字节还原；`Utf8ToUnicode("中文")` 给 `0x4E2D, 0x6587` 并能还原回同一段 UTF-8 —— 这条同时证明 OHOS 上没有走 locale/iconv |
| 6 | 7 | **鸿蒙特有 B（多线程纯函数逐位可复现）**：4 个 bionic `std::thread` 各自用固定 LCG 生成字符串，反复调用 `Split`/`Join`/`StringFormat`/`Trim`/`Utf8ToUnicode`/`UnicodeToUtf8`，把每轮的 64 位哈希累加；4 个线程的校验和必须与单线程参考逐位一致 |

## 6. 本地预验证

- **WSL Ubuntu-22.04（cmake 3.22.1 / g++ 11.4 / gtest 1.11，x86_64）**：
  打上两个 patch 后 `cmake -DENABLE_UNIT_TESTS=ON` + `ctest -V` →
  `100% tests passed, 0 tests failed out of 2`，其中
  `[==========] 25 tests from 8 test suites ran.` / `[  PASSED  ] 25 tests.`。
  对照实验（不打 patch 0001，build 目录与源码目录平级）→
  `50% tests passed, 1 tests failed out of 2`，失败的是 4 个用 fixture 的用例。

## 7. 随包内容

- `include/limonp/*.hpp`（9 个头文件）
- `lib/cmake/limonp/limonp-config.cmake`（上游 `install(EXPORT limonp ...)` 的产物）
- `licenses/LICENSE`（MIT）

## 8. 复现命令

```bash
conan create . --version=1.0.2 -pr:h=ci/conan/profiles/ohos-aarch64
```
