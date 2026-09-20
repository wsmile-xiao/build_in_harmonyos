# `enable_testing()` 落在子目录 ⇒ build 根目录 `ctest` 零执行却退出码 0；`install(TARGETS ... LIBRARY)` 漏发静态库与伞头文件；Conan CMakeDeps 顶掉 FindGTest 旧式 target 名

> DRAFT-memtailor-1.4-subdir-ctest-false-pass-install-static-and-conan-gtest-targets
> （知识库扩展草稿，路径 B）与 memtailor 1.4 归档同 PR 交付。

memtailor 本身是个没什么平台特殊性的库（CMake ≥ 3.12，静态库，运行时只链
`Threads::Threads`，源码里没有一处 `#ifdef __OHOS__` 的需要）。它值得写成一条
知识条目的原因恰恰是：**上游 CMake 里有三个「绿得看不出来」的坑**，每一个都能
让一个只判退出码的配方在没干任何事的情况下拿到绿色。

---

## 场景一：`enable_testing()` 写在子目录 ⇒ build 根目录 `ctest` 零执行却退出码 0

上游把 `include(CTest)` 写在 **`src/CMakeLists.txt`（子目录）** 而不是顶层：

```cmake
# src/CMakeLists.txt:25
include(CTest)
if(BUILD_TESTING)
  add_executable(memtailor-unit-tests ...)
  gtest_discover_tests(memtailor-unit-tests TEST_PREFIX unit-tests:)
```

`include(CTest)` 会 `enable_testing()`，而 **CMake 只在「调用
`enable_testing()` 的那个目录及其子目录」生成 `CTestTestfile.cmake`**。于是：

```
<build>/src/CTestTestfile.cmake      ← 存在（gtest_discover_tests 注册的 22 个用例）
<build>/CTestTestfile.cmake          ← 不存在
```

在 build 根目录跑 `ctest`：

```
Test project <build>
No tests were found!!!
```

**退出码是 0。** 一个配方若只写 `self.run("ctest ...")` 依赖退出码，就会在
"一个用例都没跑"的情况下拿到绿色 —— 这是本项目里最容易踩、也最隐蔽的一类假阳性。

**本包的处理有两层**：

1. patch 0001 把 `include(CTest)` 从 `src/CMakeLists.txt` 提到顶层
   （`find_package(Threads ...)` 之后），让 build 根目录的 `ctest` 真正能看到
   用例。这是**可向上游提交的正当修复**：`enable_testing()` 的作用域写错了，
   不是"为了绕 CI 才改的"。补丁同时也把子目录里那行删掉，避免重复。
2. `build()` 里仍然**解析 ctest 汇总行**而不是只看退出码：

```python
_CTEST_SUMMARY = re.compile(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)")
...
if "No tests were found" in text:
    raise ConanException("ctest found no tests ...")      # 先单独判空套件
m = _CTEST_SUMMARY.search(text)
if m is None:
    raise ConanException("ctest summary line not found")
failed, total = int(m.group(2)), int(m.group(3))
if failed != 0 or total < CTEST_EXPECTED_TESTS: raise ...
```

**判定信号（写 `build()` 之前扫一遍）**：

1. `grep -n 'include(CTest)\|enable_testing()' **/CMakeLists.txt` 命中位置是不是
   顶层目录；
2. 若在子目录，`ctest` 必须在 build 根目录跑一次、**同时看输出与 `$?`**，确认
   是 `No tests were found!!!` 而非 `0% tests passed, 0 tests failed out of N`。

---

## 场景二：`install(TARGETS ... LIBRARY DESTINATION lib)` 漏发静态库与伞头文件

上游顶层 `CMakeLists.txt` 是：

```cmake
set_target_properties(memtailor PROPERTIES PUBLIC_HEADER src/memtailor.h)
install(TARGETS memtailor LIBRARY DESTINATION lib)     # ← 只声明 LIBRARY
install(DIRECTORY src/memtailor
  DESTINATION include
  FILES_MATCHING PATTERN "*.h")
```

两个漏洞，而且**都不会报错，只是静静地少装东西**：

| 写法 | 后果 |
|------|------|
| `install(TARGETS memtailor LIBRARY DESTINATION lib)` | 静态库属于 **`ARCHIVE`** 类别；CMake 只认 `LIBRARY`，于是包目录里根本没有 `lib/libmemtailor.a` |
| `PUBLIC_HEADER` 只写了**属性**、install 规则里没有 `PUBLIC_HEADER DESTINATION` | 伞头文件 `src/memtailor.h` 不会被安装；只有 `src/memtailor/` 那棵树装出去了 |

结果是包"看起来"是成功的（configure/build/install 全绿），但消费者
`-lmemtailor` 链接失败、`#include <memtailor.h>` 直接 file not found —— 很容易
误判成"上游这个库有毛病"。

patch 0001 补齐后实测的安装树：

```
include/memtailor.h                  ← 伞头文件（原本漏装）
include/memtailor/{Arena,ArenaVector,BufferPool,MemoryBlocks,stdinc}.h
lib/libmemtailor.a                   ← 原本漏装
licenses/memtailor/{README.md,license.txt}
```

**判定信号**：`grep -n 'install(TARGETS' CMakeLists.txt` 后，问一句
"这个 target 到底是 `ARCHIVE`（静态库）还是 `LIBRARY`（共享库）？"；
只要有 `PUBLIC_HEADER` 属性，就一定要有 `PUBLIC_HEADER DESTINATION`。

---

## 场景三：Conan CMakeDeps 的 `GTestConfig.cmake` 顶掉 `FindGTest` 的旧式 target 名

上游 `src/CMakeLists.txt`：

```cmake
if(GTEST_FOUND)
  target_link_libraries(memtailor-unit-tests memtailor GTest::GTest GTest::Main)
```

`GTest::GTest` / `GTest::Main` 是 **CMake 自带 `FindGTest.cmake` 模块**创建的
旧式别名。而 Conan 的 `gtest` 由 **CMakeDeps** 生成 `GTestConfig.cmake`，其
`package_info()` 只声明四个组件目标：

```
GTest::gtest   GTest::gtest_main   GTest::gmock   GTest::gmock_main
```

`find_package(GTest)` 走的是 "config mode 优先"：`GTestConfig.cmake` 一旦先被
找到，`GTEST_FOUND` 就是 `TRUE`，**`FindGTest.cmake` 不会再被加载**，那两个旧
名字也就不存在 —— configure 期直接 `target not found`。

修法与 `archives/b/biosoup/0.10.0`、`archives/e/entt/4.0.0` 同类：

```diff
-    target_link_libraries(memtailor-unit-tests memtailor GTest::GTest GTest::Main)
+    target_link_libraries(memtailor-unit-tests memtailor GTest::gtest GTest::gtest_main)
```

---

## 场景四：`find_package(GTest)` 失败时 configure 期联网拉 googletest

上游在同一段里的 `else()` 分支是：

```cmake
FetchContent_Declare(googletest
  GIT_REPOSITORY https://github.com/google/googletest.git
  GIT_TAG        v1.16.0)
```

—— **在 configure 期 git clone**。CI worker 不可联网，走到这里就是白跑一轮。

只要让 `find_package(GTest)` 成功，这个分支就不会被走到。本包用：

```python
def requirements(self):
    self.test_requires("gtest/1.17.0.1")   # ohpcd 已发布：OHOS/armv8/clang15/libc++/cppstd17
```

选 `1.17.0.1` 而不是 `1.17.0`：前者的 `package_info()` 声明了
`gtest_main → GTest::gtest_main` 组件（场景三需要），后者是扁平的 `gtest::gtest`
布局、没有 `GTest::gtest_main`。

---

## 场景五：rule4 口径 —— 钉版 tag 的用例数 ≠ 评审朴素扫描的默认分支用例数

memtailor 上游的 `src/test/` 只有三个 TU，且**全文件没有任何 `#if` 门控 `TEST`
注册**（master 的 `ArenaTest.cpp` 里有 5 处 `#ifdef MEMT_DEBUG`，但都在
`TEST(...)` **函数体内部**包断言，不影响注册）。

| 扫描对象 | ArenaTest | BufferPoolTest | MemoryBlocksTest | 合计 |
|----------|-----------|----------------|------------------|------|
| 钉版 `v1.4` tarball | 12 | 6 | 4 | **22** |
| 默认分支 `master`（head `0a2afc3fff`, 2026-09-18） | 16 | 6 | 4 | **26** |

master 多出的 4 个是 `Arena/FreeAllAllocs`、`Arena/GuardAfterEmptyRestore`、
`Arena/GuardFreesNewerBlocks`、`Arena/EmptyBlockIsNotKeptBehindFrontBlock` ——
它们**不在 1.4 的 tarball 里**。

**所以声明的 N 必须是 26（master 朴素扫描），不是 22（钉版）。** 实测执行集是
22/22（100%），未执行 4 个按"master 有、钉版 tarball 无"逐条归因。声明 22 会
在 rule4「少报」上翻车 —— 这也是我们在 tiny-dnn 那单上学到的同一条口径。

可复现的统计命令：

```bash
# 钉版
curl -sSL https://github.com/Macaulay2/memtailor/archive/refs/tags/v1.4.tar.gz \
  | tar xz -C /tmp && grep -rc 'TEST(' /tmp/memtailor-1.4/src/test/*.cpp | paste -sd+ | bc   # 22
# 默认分支（评审口径）
curl -sSL https://codeload.github.com/Macaulay2/memtailor/tar.gz/refs/heads/master \
  | tar xz -C /tmp && grep -rc 'TEST(' /tmp/memtailor-master/src/test/*.cpp | paste -sd+ | bc  # 26
```

---

## 与已有条目的关系

- `DRAFT-box2d-2.4.1-ctest-empty-suite-false-pass`：同样是"ctest 空套件退出码 0
  的假阳性"，但**根因不同** —— Box2D 是上游**根本没有** `add_test()`；memtailor
  是 `enable_testing()` 的**作用域**落在了子目录。两条的处理也不一样：Box2D 只能
  放弃 ctest 直接跑二进制（本条目把它列为 fallback），memtailor 可以把
  `include(CTest)` 提到顶层做**正当修复**。
- `DRAFT-tiny-dnn-1.0.0a3-...-network-gtest-substitution`：共享"上游 configure 期
  联网拉 gtest ⇒ 用 Conan `test_requires` 替换"与"朴素扫描 N 取默认分支"两条。
