# memtailor 1.4 — HarmonyOS PC 适配笔记

## 1. 概览

| 项 | 值 |
|----|----|
| 上游 | https://github.com/Macaulay2/memtailor |
| 版本 | 1.4（git tag `v1.4`） |
| 源码 | `https://github.com/Macaulay2/memtailor/archive/refs/tags/v1.4.tar.gz` |
| SHA256 | `d16726040d73751d220f2a2d6404a74b2a3f7d2d7a62d11d69f845bafce55136` |
| 构建 | CMake ≥ 3.12（上游另有 autotools 构建，本包只走 CMake） |
| 包类型 | static-library |
| 依赖 | 运行时零依赖（只链接 `Threads::Threads`）；测试期 `test_requires gtest/1.17.0.1` |

memtailor 是 Macaulay2 / Frobby 生态里的专用内存分配器库，提供两类分配器：

- **`memt::Arena`**：栈式（LIFO）分配器，后备块按几何级数增长
  （`growCapacity()`：新块 = max(所需, 当前块) × 2，且不小于
  `16*1024 - sizeof(Block) - 16`）；
- **`memt::BufferPool`**：固定尺寸缓冲池，内部是 free list。

外加一个从 Arena 取内存的 `ArenaVector<T, bool FreeMemory>`。

## 2. 三个上游缺陷（本包用两个 patch 修掉）

### 2.1 `GTEST_FOUND` 恒假 → configure 期去 GitHub 拉 googletest（patch 0002）

上游 `src/CMakeLists.txt`：

```cmake
  if(NOT GTEST_FOUND)
    find_package(GTest)
  endif()
  include(GoogleTest)
  gtest_discover_tests(memtailor-unit-tests TEST_PREFIX unit-tests:)

  if(GTEST_FOUND)
    target_link_libraries(memtailor-unit-tests memtailor GTest::GTest GTest::Main)
  else()
    include(FetchContent)
    FetchContent_Declare(googletest
      GIT_REPOSITORY https://github.com/google/googletest.git
      GIT_TAG        v1.16.0)
    FetchContent_MakeAvailable(googletest)
```

这里有**两个独立缺陷，必须一起修** —— 只修一个仍然 configure 失败。

**(a) `GTEST_FOUND` 这个全大写变量根本不会被定义。**
`find_package(GTest)` 走的是 **CONFIG 模式**（CMakeDeps 生成的
`GTestConfig.cmake` / `gtest-config.cmake`）。CONFIG 模式下 CMake 只保证设置
`<PackageName>_FOUND`，也就是 **`GTest_FOUND`**；全大写的 `GTEST_FOUND` 是
CMake 自带 **`FindGTest.cmake` 模块**（MODULE 模式）才会设置的遗留变量。
CONFIG 一旦命中，`FindGTest.cmake` 就不会被加载 → `GTEST_FOUND` 恒未定义 →
`if(GTEST_FOUND)` 恒假 → 落到 `else()`，在 **configure 期**执行
`FetchContent_MakeAvailable(googletest)`：

```
[ 22%] Performing download step (git clone) for 'googletest-populate'
fatal: unable to access 'https://github.com/google/googletest.git/':
       Failed to connect to github.com port 443 after 65628 ms
CMake Error at .../FetchContent.cmake:1918 (message):
  Build step for googletest failed: 2
Call Stack: src/CMakeLists.txt:50 (FetchContent_MakeAvailable)
```

CI worker 不可联网，于是**测试一行都还没编**就 configure 失败。
注意本仓早已声明 `test_requires("gtest/1.17.0.1")`，失败点**不是**
「找不到 gtest」，而是「gtest 找到了、target 也声明了，却因为变量名大小写
没被上游认出来」—— 只看上游源码里的 `find_package(GTest)` 很容易误判。

**(b) `GTest::GTest` / `GTest::Main` 是 FindGTest.cmake 的旧式别名。**
Conan 的 `gtest/1.17.0.1` 由 CMakeDeps 生成的配置只声明四个组件目标：

```
GTest::gtest  GTest::gtest_main  GTest::gmock  GTest::gmock_main
```

所以即使 (a) 修好、真的走进了 `if` 分支，`GTest::GTest` 仍然
`target not found`。

patch 0002 同时改掉两处：

```cmake
if(GTest_FOUND OR GTEST_FOUND OR TARGET GTest::gtest)
  target_link_libraries(memtailor-unit-tests memtailor GTest::gtest)
```

- 判断条件三种写法都接受，并以 **target 存在性兜底**，不再依赖任何
  `*_FOUND` 变量的拼写；
- 只链 `GTest::gtest` 而**不链** `GTest::gtest_main`：上游
  `src/test/testMain.cpp` 自带 `main()`（`InitGoogleTest` + `RUN_ALL_TESTS`），
  再链 gtest_main 就是多一份 `main` 定义（静态库的 main 一般不会被拉进来，
  但没必要留这个隐患）。

### 2.2 `ctest` 在 build 根目录「零执行却全绿」（patch 0001a）

上游把 `include(CTest)` 写在 **`src/CMakeLists.txt`（子目录）** 里，而不是
顶层 `CMakeLists.txt`。`include(CTest)` 会 `enable_testing()`，而 CMake 只在
**调用 `enable_testing()` 的那个目录及其子目录**生成 `CTestTestfile.cmake`。
于是：

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
"一个用例都没跑"的情况下拿到绿色。本包做了两件事：

1. patch 0001 把 `include(CTest)` 提到顶层，让 build 根目录的 `ctest` 真正
   能看到用例；
2. `build()` 里仍然**解析 ctest 汇总行**而不是只看退出码 —— 先对
   `No tests were found` 单独判失败，再要求
   `100% tests passed, 0 tests failed out of 22` 且总数 ≥ 22。

### 2.3 静态库与伞头文件都没被安装（patch 0001b）

上游顶层 `CMakeLists.txt`：

```cmake
set_target_properties(memtailor PROPERTIES PUBLIC_HEADER src/memtailor.h)
install(TARGETS memtailor LIBRARY DESTINATION lib)
install(DIRECTORY src/memtailor DESTINATION include FILES_MATCHING PATTERN "*.h")
```

两个漏洞：

- `install(TARGETS ... LIBRARY DESTINATION lib)` **只声明 LIBRARY**。静态库
  属于 `ARCHIVE` 类别，CMake 不会把它装出去 —— 包目录里 `lib/libmemtailor.a`
  根本不存在。
- `memtailor.h` 只挂在 `PUBLIC_HEADER` **属性**上，install 规则里没有
  `PUBLIC_HEADER DESTINATION`，于是伞头文件也不会被安装 —— 消费者
  `#include <memtailor.h>` 直接 file not found（只有 `memtailor/` 那棵树装出去了）。

patch 0001 把两者补齐，安装结果（实测）：

```
include/memtailor.h                  ← 伞头文件（原本漏装）
include/memtailor/{Arena,ArenaVector,BufferPool,MemoryBlocks,stdinc}.h
lib/libmemtailor.a                   ← 原本漏装
licenses/memtailor/{README.md,license.txt}
```

### 2.4 附：configure 期联网拉 googletest

上游 `find_package(GTest)` 之后的分支：

```cmake
FetchContent_Declare(googletest
  GIT_REPOSITORY https://github.com/google/googletest.git
  GIT_TAG        v1.16.0)
```

CI worker 不可联网。本包用 `test_requires("gtest/1.17.0.1")`
（ohpcd 已发布：OHOS/armv8/clang15/libc++/cppstd17）让 `find_package(GTest)`
命中 Conan 的 CMakeDeps 配置。但**光有依赖不够** —— 上游判空用的变量名
`GTEST_FOUND` 与 CONFIG 模式实际设置的 `GTest_FOUND` 不同名，见 2.1(a)，
必须靠 patch 0002 改写判断条件才会真正走进 `if` 分支。`else()` 分支本身
保留不动（不删上游代码）。

## 3. 上游测试：22 个用例，无门控，全量实跑

| 文件 | TEST 宏 |
|------|---------|
| `src/test/ArenaTest.cpp` | 12 |
| `src/test/BufferPoolTest.cpp` | 6 |
| `src/test/MemoryBlocksTest.cpp` | 4 |
| **合计** | **22** |

三个文件通读后**没有任何 `#if` / `#ifdef` / `#ifndef` / `#endif`**，也没有
被注释掉的 `TEST(` —— 所以"朴素文本扫描 22"与"实际注册 22"完全一致，不存在
tiny-dnn 那种口径差。上游 `.github/workflows/build.yml` 的 cmake 分支是
`cmake -B. -S.. -GNinja && ninja && src/memtailor-unit-tests`（**直接跑二进制**），
测试经 `gtest_discover_tests(memtailor-unit-tests TEST_PREFIX unit-tests:)`
展开为 22 个独立 CTest 用例。本包在 `build()` 内用 ctest 全量实跑。

## 4. OHOS 平台相关的可观测行为

- **对齐契约就是平台宽度**：`stdinc.h:101`
  `MemoryAlignment = static_cast<unsigned int>(sizeof(void*))`。
  aarch64/OHOS 上是 **8**，32 位 ARM 的 OHOS 会是 4。`Arena::alloc()` 与
  `BufferPool::alloc()` 都保证返回地址整除它。
  另外 `BufferPool` 的实际缓冲尺寸是 `align(max(请求值, sizeof(FreeNode)))`，
  `FreeNode` 就是一个 `pointer` —— 所以 `BufferPool(1).getBufferSize()`
  在 aarch64 上恰好等于 `sizeof(void*)` == 8。
- **memtailor 自身不是线程安全的**（文档明示一个 Arena/BufferPool 只给一个
  线程用），OHOS 上要验证的是"每线程各持一份时，bionic 的 std::thread +
  `operator new/delete` 下的行为逐位可复现"，而不是"共享分配器是安全的"。
- **后备内存来自 `new char[]`**（`MemoryBlocks.cpp:37`），因此首块地址满足
  `__STDCPP_DEFAULT_NEW_ALIGNMENT__`，再加上 position 只按 MemoryAlignment
  的整数倍推进，8 字节对齐这条契约在 aarch64 上恒成立。

## 5. 消费者测试（test_package）六组断言

| 组 | 退出码 | 判据 |
|----|--------|------|
| 1 | 2 | `libmemtailorIsPresent()` 可链接 + `MEMTAILOR_VERSION_STRING == "1.4"` + 伞头文件与三个公开头都在 include 根下（安装布局断言） |
| 2 | 3 | Arena：LIFO 复用同一地址、`alloc(0)` 给唯一非空地址、64KB 触发几何增长、`freeAllAllocsAndBackingMemory()` 归零 |
| 3 | 4 | `ArenaVector<T,true>` 析构归还内存 / `<T,false>` 保留内存；两种模式下元素的构造/析构都配平 |
| 4 | 5 | BufferPool：fresh 池 `getMemoryUse()==0`、free list 复用同一块、`fromPool()` 认得活缓冲、释放后备内存后仍能继续分配 |
| 5 | 6 | **鸿蒙特有 A**：`MemoryAlignment == sizeof(void*) == 8`；Arena 连续 64 次不同大小申请、BufferPool 连续 64 次申请的每个返回值都 8 字节对齐；`BufferPool(1).getBufferSize() == sizeof(void*)` |
| 6 | 7 | **鸿蒙特有 B**：4 个 `std::thread`（bionic pthread）各自持有一份 Arena+BufferPool，各做 4000 次确定性 LCG 驱动的分配/释放（含活缓冲内容复核，重叠分配会被抓到），校验和必须与单线程参考逐位一致 |

## 6. 本地预验证

- **WSL Ubuntu-22.04（g++ 11.4，x86_64）**：打上两个 patch 后
  `cmake -DBUILD_TESTING=ON` + `ctest` → **22/22 通过**；`cmake --install`
  产物为 `include/memtailor.h` + `include/memtailor/*.h` + `lib/libmemtailor.a`；
  消费者测试 `g++ -std=c++17 -Wall -Wextra` **零告警**编译，6 组断言全绿。
- **OHOS native SDK（clang 15.0.4，`--target=aarch64-linux-ohos`）**：
  库的四个 TU + 消费者测试一起 `-std=c++17 -Wall -Wextra` 交叉编译
  **零告警零错误**，产出 `ELF64 / AArch64 / DYN`。

  未打 patch 前的对照：在 build 根目录 `ctest` → `No tests were found!!!`，
  退出码 0（复现 §2.2）。

## 7. 随包内容

- `include/memtailor.h` + `include/memtailor/*.h` + `lib/libmemtailor.a`
- `licenses/LICENSE`（上游 Modified BSD，源文件名为 `license.txt`）

## 8. 复现命令

```bash
conan create . --version=1.4 -pr:h=ci/conan/profiles/ohos-aarch64
```
