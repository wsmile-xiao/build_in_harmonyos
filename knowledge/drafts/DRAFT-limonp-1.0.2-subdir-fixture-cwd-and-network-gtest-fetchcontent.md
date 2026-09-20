# 上游 fixture 相对路径 + `ADD_TEST` 相对 COMMAND + 默认 WORKING_DIRECTORY 只在「build 是源码根直接子目录」时成立；configure 期 FetchContent 联网拉 gtest；ctest 一个二进制算一个用例吞掉 gtest 汇总行

> DRAFT-limonp-1.0.2-subdir-fixture-cwd-and-network-gtest-fetchcontent
> （知识库扩展草稿，路径 B）与 limonp 1.0.2 归档同 PR 交付。

limonp（yanyiwu/limonp，cppjieba 作者抽出的 header-only 基础设施库：StringUtil /
Logging / Config / LocalVector / Closure / ArgvContext / Colors）是那种"看起来
零依赖、应该很好打包"的库 —— 9 个公共头，`add_library(limonp INTERFACE)`，
`install(DIRECTORY include/ ...)`。它的坑全部在**测试侧**，而且是三个互相独立、
都只在 out-of-tree 构建下才现形的坑。

## 场景一：fixture 相对路径 + 相对 `ADD_TEST` COMMAND，只在 in-tree 构建下成立

上游顶层 `CMakeLists.txt`：

```cmake
ENABLE_TESTING()
ADD_SUBDIRECTORY(test)
ADD_TEST(NAME ./test/demo     COMMAND ./test/demo)
ADD_TEST(NAME ./test/test.run COMMAND ./test/test.run)
```

而三个用例 TU 用**相对 cwd 的路径**打开 fixture：

| 文件 | 打开的 fixture |
|------|----------------|
| `test/unittest/TConfig.cpp` | `../test/testdata/test_config.ini` |
| `test/unittest/TStdExtension.cpp` | `../test/testdata/…` |
| `test/unittest/TStringUtil.cpp` | `../test/testdata/…` |

这套写法隐含了两个前提，且**都只在"build 目录恰好是源码根的直接子目录"时成立**：

1. CTest 在没有 `WORKING_DIRECTORY` 属性时用 **build 目录**当 cwd，
   `../test/testdata/...` 于是解析成 `<source>/test/testdata/...` ✅；
2. `COMMAND ./test/demo` 是**相对 WORKING_DIRECTORY**（也就是 build 目录）
   解析的，而上游又把 `EXECUTABLE_OUTPUT_PATH` 设成
   `${PROJECT_BINARY_DIR}/test`，所以 `<build>/test/demo` ✅。

上游 CI 用 `cmake -B ${github.workspace}/build` —— build 就在源码根下面，
两个前提同时满足，所以上游一直是绿的。

**Conan 的 `cmake_layout()` 把 build 目录放进本地缓存、与 source 目录互为兄弟**，
两个前提同时失配。实测（源码 `/tmp/LM/src-unpatched`、build `/tmp/LM/b-unpatched`，
**真正的兄弟节点**）：

```
50% tests passed, 1 tests failed out of 2
```

（测试顺序随机，具体是 demo 还是 test.run 先失败不稳定；失败的那个是
test.run —— 4 个 fixture 用例 `Unable to open file`。）

**判定信号（写补丁之前扫一遍）**：

```bash
grep -rn '\.\./' test/                      # fixture 用相对 cwd 的路径
grep -n  'ADD_TEST' CMakeLists.txt          # COMMAND 是不是相对路径
grep -n  'WORKING_DIRECTORY' CMakeLists.txt # 有没有显式 cwd
```

三条同时命中 + 上游 CI 的 build 是源码根子目录 → 必然踩。

### 修法（patch 0001）：`WORKING_DIRECTORY` 与 `$<TARGET_FILE:...>` **必须一起改**

```diff
 ADD_SUBDIRECTORY(test)
-ADD_TEST(NAME ./test/demo COMMAND ./test/demo)
-ADD_TEST(NAME ./test/test.run COMMAND ./test/test.run)
+ADD_TEST(NAME ./test/demo COMMAND $<TARGET_FILE:demo>)
+ADD_TEST(NAME ./test/test.run COMMAND $<TARGET_FILE:test.run>)
+SET_TESTS_PROPERTIES(./test/demo ./test/test.run
+        PROPERTIES WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}/test")
```

**只改 `WORKING_DIRECTORY` 不改 `COMMAND` 会更糟**：`./test/demo` 会被解析成
`<source>/test/test/demo`，从"fixture 打不开"变成"二进制找不到"，而 ctest 汇总行
仍然是 `50% tests passed, 1 tests failed out of 2`，症状几乎一样，极易误判成
"补丁没生效"。`$<TARGET_FILE:...>` 让可执行文件的位置与 cwd 解耦：二进制按
target 定位，cwd 按我们需要设成 `<source>/test`（`../test/testdata/...` 在这里
正好解析成 `<source>/test/testdata/...`）。

改完实测：`100% tests passed, 0 tests failed out of 2`，且 `ctest -V` 里带出
`[  PASSED  ] 25 tests.`。

这个补丁是**可向上游提交**的（满足 P005）：它把"依赖 build 目录位置"的隐含假设
变成显式的 cwd 声明，in-tree 与 out-of-tree 两种布局都正确，不引入任何
平台相关性。

## 场景二：`test/unittest/CMakeLists.txt` 在 configure 期联网 git clone googletest

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

两个问题叠在一起：

1. **`FetchContent_*` 在 configure 期联网** —— CI worker 不联网，
   configure 阶段直接挂，白跑一轮（本赛事 CI 排队 ~2.5-3 小时）。
2. **裸 target 名 `gtest`** —— `FetchContent_MakeAvailable` 会把 googletest
   的 CMake 目标直接带进当前工程，所以能写裸 `gtest`。换成 Conan 的
   CMakeDeps 之后目标名是 **`GTest::gtest`**（由 `gtest/1.17.0.1` 的
   `package_info()` 声明，`cmake_file_name = "GTest"`）。

### 修法（patch 0002）

```diff
-include(FetchContent)
-FetchContent_Declare(
-  googletest
-  GIT_REPOSITORY https://github.com/google/googletest.git
-  GIT_TAG release-1.12.1
-)
-FetchContent_MakeAvailable(googletest)
+find_package(GTest REQUIRED)
...
-TARGET_LINK_LIBRARIES(test.run gtest)
+TARGET_LINK_LIBRARIES(test.run GTest::gtest)
```

配方侧：

```python
def requirements(self):
    self.test_requires("gtest/1.17.0.1")   # 仅测试期，不进 package 依赖图
```

### ★ 只能链 `GTest::gtest`，**不能**链 `GTest::gtest_main`

`test/unittest/gtest_main.cpp` 是从 googletest 里拷贝来的一份**自带 `main()`**
的文件（`GTEST_API_ int main(int argc, char** argv) { ... }`），并且被列在
`ADD_EXECUTABLE(test.run ...)` 里。`GTest::gtest_main` 提供的也是 `main` ——
链上去就是 **duplicate symbol main**。

> 同类陷阱：`gtest/1.17.0`（无 `.1`）在 ohpcd 上是**扁平布局**，只有
> `gtest::gtest`，**没有** `GTest::gtest_main` / `GTest::gmock_main`；
> `gtest/1.17.0.1` 才有完整 `GTest::*` 目标名。用哪个版本要按
> `package_info()` 实际声明的 target 名来写，别按印象写。

## 场景三：ctest 把整个 gtest 二进制当 **1 个用例**，`--output-on-failure` 还会吞掉汇总行

上游顶层注册的是 **2 个 ctest 用例**（`./test/demo` 与 `./test/test.run`），
而 `test.run` 内含 **25 个 gtest TEST**。这带来两个可观测性陷阱：

| 陷阱 | 后果 |
|------|------|
| 只解析 ctest 汇总行 `2/2` | `test.run` 内部的 25 个用例缩水到 3 个，汇总行**仍然是 2/2**，完全看不出来 |
| `ctest --output-on-failure` | 只打印**失败**用例的输出 —— 通过的 test.run 一个字节都不输出，连 gtest 自己的 `[  PASSED  ] 25 tests.` 都看不到 |

所以配方 `build()` 里必须用 **`ctest -V`**（verbose，把每个用例的输出都带回来），
再对 **gtest 自己的汇总行**做 hard check：

```python
log = os.path.join(self.build_folder, "ctest.log")
self.run('ctest -V > "{}" 2>&1 || true'.format(log), cwd=self.build_folder)
# 硬校验（任一不满足即 raise）：
#   - "No tests were found" 不能出现
#   - 必须有 ctest 汇总行 (\d+)% tests passed, (\d+) tests failed out of (\d+)
#   - failed == 0 且 total >= CTEST_EXPECTED_TESTS(=2)
#   - 不能出现 "[  FAILED  ]"
#   - 必须有 gtest 的 "[  PASSED  ] N tests."，且 N >= GTEST_EXPECTED_TESTS(=25)
```

前两类信号分开看是必要的：ctest 汇总行证明**两个可执行文件都跑了**，
gtest 汇总行证明**test.run 里的用例集没缩水**，缺一不可。

## 场景四：rule4 口径 —— 朴素扫描 N ≠ 实际注册用例数

| 口径 | limonp 数值 | 说明 |
|------|-------------|------|
| 上游**默认分支 master** 朴素扫描 `TEST(` | **27** | 评审的"上游实测 N"用的是这个 |
| 钉版 `v1.0.2` 朴素扫描 | 26 | |
| 真正注册进 `test.run` 并执行 | **25** | |

差值逐项可归因：

| 类别 | 数 | 原因 |
|------|----|------|
| `TCastFloat.cpp` | 1 | 有 `TEST(CastFloat, ...)` 宏，但**没有被写进 `ADD_EXECUTABLE(test.run ...)`**，所以既不注册也不执行 |
| master 新增 `TEST(LocalVector, NonTrivialValue)` | 1 | master 的 `TLocalVector.cpp` 比 v1.0.2 多 1 个 TEST（且顺手把 `capacity()` 断言从 `LOCAL_VECTOR_BUFFER_SIZE` 改成 `0u`/`ASSERT_GE` —— 上游后续行为变更，与本包无关） |

**对 rule4 直接有用**：声明 N 取**上游默认分支 master 的朴素扫描值 27**（不是
钉版 26，更不能拿实际注册的 25 去声明 —— 会在"少报"上翻车），未执行数
Z = 27 − 25 = **2**，并能逐类归因。body 里写成：

```
- 上游测试用例通过率：**执行集 25/25（100%）**；**相对上游全集 27，未执行 2 个**
```

（另注：本包在 `build()` 里跑的是 `ctest -V` 覆盖的 **2 个 ctest 用例**，
两者是不同粒度，body 里要分别写清，避免"2/2 也叫 100%"的口径混淆。）

## 场景五：aarch64 上才是"可观测"的两条平台契约

limonp 本身没有平台相关代码路径，但有两处行为在 aarch64/OHOS 上**必须实测**
才能确认（x86 上跑通不代表 aarch64 上对）：

1. **`char` 的默认有符号性**：aarch64-linux（含 OHOS）的 `char` 是
   **unsigned**，x86-linux 是 **signed**。GBK 的 `中` = 字节 `D6 D0`，
   `0xD6` 在 x86 的 `signed char` 里是 **-42**。`StringUtil.hpp` 的
   `TwocharToUint16` 用 `uint16_t(high) & 0x00ff`（**先转无符号再掩码**）
   吃掉符号位，所以两端都必须得到 `0xD6D0`。
   另注：limonp 的 GBK↔Unicode 是**字节对打包**（不是查表映射），
   不依赖平台 locale / iconv —— OHOS/bionic 两样都没有，这条往返只能靠
   这段纯计算代码，必须在 aarch64 上逐位一致。
2. **`IsSpace(unsigned)` 的 `> 0xff` 越界早退**：上游注释明说"把大整数喂给
   `isspace` 会 core dump"。`wchar_t` 在 aarch64/OHOS 上是 **4 字节**
   （Windows 上 2 字节），`IsSpace(1000024u)` 必须返回 `false`，而不是把
   `1000024 & 0xff` 拿去查 ctype 表。

这两条写进了消费者的**鸿蒙特有断言**（rule12），断言的是**可观测行为**
（返回值 / 字节序列），不是 grep 出来的符号名。
