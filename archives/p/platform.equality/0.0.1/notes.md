# platform.equality 0.0.1 — OHOS 适配说明

## 库概述

`platform.equality` 是 [linksplatform/Equality](https://github.com/linksplatform/Equality) 的
C++20 **header-only** 库（4 个公共头，CMake 里为 `add_library(... INTERFACE)`），
提供两条能力：

1. **`std::any` 的运行期类型分派相等比较** —— 通过
   `std::unordered_map<std::type_index, EqualityComparerFunctionType<std::any>>`
   注册表按 `typeid` 查找比较器，实现 `std::any == std::any`；
   未注册类型抛 `std::runtime_error`，并支持 `RegisterEqualityComparer<T>()` 运行期注册。
2. **`std::ranges::range` 的 `std::equal_to` 偏特化** —— 对满足 `std::ranges::range`
   且非 `std::equality_comparable` 的类型，`std::equal_to` 用它做逐元素比较。

无运行时依赖，零外部依赖。

## 适配要点（两处 OHOS 平台差异 + 一处构建调整）

### 1. OHOS libc++ 默认裁剪 `<ranges>` 算法族（**核心问题**）

`Platform.Equality.Range.h:18` 的实现是：

```cpp
return std::ranges::equal(left, right);
```

在 OHOS SDK（clang 15.0.4，libcxx-ohos）上编译报错：

```
Platform.Equality.Range.h:18:20: error: no member named 'equal' in namespace 'std::ranges';
                                     did you mean simply 'equal'?
note: 'equal' declared here        # 指向 <__algorithm/equal.h> 的传统迭代器版
note: candidate function template not viable: requires 4 arguments, but 2 were provided
```

**诊断陷阱**：报错看起来像"忘了 `#include <algorithm>`"，但：

- `Range.h` **已经**包含 `<algorithm>`；
- 补 `#include <ranges>` 也**无效**（已实测）；
- 头文件确实存在，且 `algorithm:1794` 确实 `#include <__algorithm/ranges_equal.h>`。

真实原因是**条件编译裁剪了整个 ranges 算法族**
（`libcxx-ohos/include/c++/v1/__algorithm/ranges_equal.h:24`）：

```cpp
#if _LIBCPP_STD_VER > 17 && !defined(_LIBCPP_HAS_NO_INCOMPLETE_RANGES)
```

OHOS 默认未定义 `_LIBCPP_ENABLE_EXPERIMENTAL`，而该宏正是 `__config` 中取消
`_LIBCPP_HAS_NO_INCOMPLETE_RANGES` 定义的开关，因此 `std::ranges` 只剩
concepts/views 的一部分，**算法一族整体缺席**。

> 该问题在上游 CI 不复现：GCC 的 libstdc++ 不裁剪 ranges。header-only 库尤其隐蔽
> —— 库本体不编译，直到消费者或测试 TU 实例化模板才报错。

**修复**：`conanfile.py` 的 `generate()` 中，当 `os == "OHOS"` 时注入
`-D_LIBCPP_ENABLE_EXPERIMENTAL`（libc++ 官方实验特性总开关，非 hack）。
选择在配方侧全局注入而非逐个源文件打补丁，因为本库是 header-only，没有"源文件"可打。

### 2. `Platform.Equality.Any.h` include 不自洽

该头使用了 `std::string`（`EQUALITY_COMPARER(std::string)`）与 `std::unordered_map`
（`AnyEqualityComparers`），却只包含了 `<any> / <concepts> / <stdexcept> / <typeindex>`。

- GCC 上靠 `<gtest/gtest.h>` 传递包含（transitively）侥幸编过；
- OHOS libc++ 上直接报
  `implicit instantiation of undefined template 'std::basic_string<char>'`。

**修复**：`patches/0001-self-contained-headers-ohos.patch` 补齐
`<string>`、`<unordered_map>`（及 `Range.h` 的 `<ranges>`），使头文件自洽。
**只改库头文件，上游测试源文件一字未改。**

### 4. gtest 必须经 CMakeDeps 解析（本地检视第 3 轮 P2-1）

主配方原先只 `CMakeToolchain(self)`，CMakeLists 却用 `find_package(GTest REQUIRED)`
——`GTestConfig.cmake` 由 **CMakeDeps** 生成，`CMakeToolchain` 不产出。缺了它，
CMake 会回退到内置 `FindGTest.cmake` 去搜系统/sysroot 的 gtest，
使 `test_requires("gtest/1.17.0")` 的 pin 形同虚设。

修复时踩到两处真实差异（均已实测确认）：

1. **包名/目标名大小写**：CMakeDeps 按 Conan 包名生成 `gtest-config.cmake`，
   暴露的是 **`gtest::gtest`**（小写）；上游自带的 config 才叫 `GTest::gtest`。
   写成 `find_package(GTest)` + `GTest::gtest` 会重新落回系统 gtest。
2. **gtest_main 不是 component**：Conan 的 gtest 配方只声明
   `cmake_target_name = "gtest::gtest"`、`libs = ["gtest"]`，
   **没有** gtest_main 的 component（尽管 `libgtest_main.a` 随包发布）。
   而上游测试源文件**没有 `main()`**，因此必须另行链接 gtest_main。
   CMakeLists 用 CMakeDeps 导出的纯路径变量 `gtest_PACKAGE_FOLDER_RELEASE`
   定位同包的 `libgtest_main.a`（不用 `INTERFACE_INCLUDE_DIRECTORIES`，
   它含 `$<CONFIG:...>` 生成器表达式，无法直接做路径运算），
   找不到时 `FATAL_ERROR` 而不是回退系统 gtest。

实测：`-- Conan: Target declared 'gtest::gtest'`、
`-- Using gtest_main: /root/.conan2/p/b/gtest.../p/lib/libgtest_main.a`，
确认为 Conan pin 的 gtest/1.17.0。

### 3. 上游测试工程不可直接使用（构建调整）

`cpp/Platform.Equality.Tests/CMakeLists.txt` 用 `FetchContent_Declare(googletest URL
https://github.com/google/googletest/archive/refs/tags/release-1.10.0.zip)`
在 **configure 期从 GitHub 拉源码** —— CI 环境不可达，且违反"依赖走 Conan 制品仓"约定。

**处理**：不使用上游 `.Tests` 子工程，改为配方自带 `CMakeLists.txt`，用 Conan 制品仓的
`gtest/1.17.0`（`build_requirements()` + `test_requires`，与 `x86-simd-sort 5.0` 同法）
编译**同一份上游测试源文件** `Platform.Equality.Tests.cpp`，保持"真实执行上游测试"的语义。

> 另注：不能使用 `gtest_discover_tests()` —— 它在**构建期执行**测试二进制来枚举用例，
> 交叉编译下二进制是 aarch64，构建机跑不了。改用 `add_test()` +
> CTest 的 `CROSSCOMPILING_EMULATOR`（`ohos-aarch64-run` profile 已配 qemu）。

## 测试结果

### 上游测试（真实执行）

`cpp/Platform.Equality.Tests/Platform.Equality.Tests.cpp`，1 个套件 `EqualityTest`，
**5 个 TEST 用例 / 15 条断言**，经 `ctest` 在 OHOS aarch64（qemu）实跑：

```
[==========] Running 5 tests from 1 test suite.
[ RUN      ] EqualityTest.BaseAnyEqual
[       OK ] EqualityTest.BaseAnyEqual (6 ms)
[ RUN      ] EqualityTest.AdvancedAnyEqual
[       OK ] EqualityTest.AdvancedAnyEqual (0 ms)
[ RUN      ] EqualityTest.AggressiveAnyTest
[       OK ] EqualityTest.AggressiveAnyTest (262 ms)
[ RUN      ] EqualityTest.RegisterTest
[       OK ] EqualityTest.RegisterTest (0 ms)
[ RUN      ] EqualityTest.RangeEquality
[       OK ] EqualityTest.RangeEquality (0 ms)
[  PASSED  ] 5 tests.
```

ctest 汇总：`100% tests passed, 0 tests failed out of 1`

### 消费者端到端用例（`test_package/test.cpp`，9 项检查）

```
ok  : std::any(int,int) 不同值 -> 不等
ok  : std::any(int,float) 类型不同 -> 不等
ok  : std::any(std::string) 等值 -> 相等
ok  : std::any(int) 与裸 int 混比
ok  : 未注册类型比较 -> 抛 runtime_error
ok  : 注册自定义比较器后 any == any
ok  : range 相等 -> equal_to 为真
ok  : range 不等 -> equal_to 为假
ok  : range 长度不同 -> equal_to 为假
checked=9 failed=0
```

## 产物

- 4 个头文件：`Platform.Equality.h`、`Platform.Equality.Any.h`、
  `Platform.Equality.Range.h`、`Platform.Equality.EqualityComparerFunctionType.h`
- LICENSE
- `package_id` 已 `self.info.clear()`（header-only，产物与编译器/构建类型无关）

## 构建验证

- **profile**：`ohos-aarch64-run`（含 qemu `CMAKE_CROSSCOMPILING_EMULATOR`）
- **编译器**：OHOS SDK clang 15.0.4，`-std=c++20`，target aarch64-unknown-linux-ohos
- **命令**（本地开发机，x86_64 宿主 → aarch64 目标；`can_run` 开关见下）：
  ```
  conan create archives/p/platform.equality/0.0.1 \
      -pr:h ohos-aarch64-run -pr:b default \
      -c tools.build.cross_building:can_run=True -c tools.build:jobs=4
  ```
- **结果**：`conan create` 退出码 **0**。

> ⚠ **`-c tools.build.cross_building:can_run=True` 不是可选项**。本机是 x86_64 宿主，
> 不加这个开关 `can_run()` 恒为 False，**层 2 的 9 条消费者断言一条都不会执行**
> （配方会打印 WARNING 后返回）。上面这条带开关的命令，才是下面两行实测结果的出处。

### 两层测试的执行口径

| 层 | 内容 | 执行方式 | 实测结果 |
|---|---|---|---|
| 层 1（上游） | `Platform.Equality.Tests.cpp` 5 用例 / 15 断言 | `build()` 内 `cmake.test()` → ctest，经 profile 的 qemu emulator | `100% tests passed, 0 tests failed out of 1` |
| 层 2（消费者） | `test_package/test.cpp` 9 项检查 | `test()` 内 `self.run(binary)` | `package layout OK` + `checked=9 failed=0` |

上表两行**均取自上述带 `can_run=True` 的同一份实跑日志**（ctest 行
`1/1 Test #1 ... Passed 0.50 sec`、消费者行 `checked=9 failed=0`）。

层 2 的自动执行与宿主能力有关，如实说明如下。

#### 关于 `can_run()` 与"静默通过"

`test()` 采用仓库通用写法（2450 个已合入配方同款）：

```python
if not can_run(self):
    self.output.warning("SKIPPED consumer test: ... No assertion was run here. ...")
    return
self.run(bin_path, env="conanrun")
```

- **CI（OHOS worker）**：profile `ci/conan/profiles/ohos-aarch64` 是**原生**构建
  （工具链 `/data/service/hnp/bin/clang++`、无 emulator、无 qemu），
  `can_run()` 为 **True**，层 2 用例**真实执行**——与层 1 一样是实跑证据。
- **本地开发机（x86_64 宿主 / aarch64 目标）**：`can_run()` 为 **False**，
  层 2 不会自动执行。此时配方打印 **WARNING** 明确记录"本机跳过、未跑任何断言"，
  **不是**静默 `return`。

> 初版曾写 `self.conf.define("tools.build.cross_building:can_run", True)`
> 强制打开开关，这会把"开发机装了 binfmt_misc qemu"这一**私有环境假设硬编码进
> 要进 CI 的配方**：一旦 CI 判定为交叉构建，就会去执行跑不起来的 aarch64 二进制，
> 直接弄红 `conan create`。已按仓库通用写法改回。

**本地想实跑层 2**，在命令行显式打开开关即可（配方内不硬编码）：

```
conan create archives/p/platform.equality/0.0.1 \
    -pr:h ohos-aarch64-run -pr:b default \
    -c tools.build.cross_building:can_run=True
```

本机已实测**该带开关的命令**下列 9 项全部执行并通过（`checked=9 failed=0`）；
该结论与文首「构建验证」里的主命令是同一条命令，口径一致。

## 已知限制

- 未做真机（DAYU200）验证：本库为纯算法/类型分派库，无设备相关行为
  （无输入设备 / 音视频 / 显示交互），qemu 执行上游测试即为充分证据。
- `AggressiveAnyTest` 内含 `while (steps--)` 的 1e6 次循环，单次约 262 ms；
  在 qemu 下累计约 0.3 s，不影响 CI。
