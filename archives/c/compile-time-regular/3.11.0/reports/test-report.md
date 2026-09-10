# compile-time-regular 3.11.0 测试报告

- 日期：2026-09-07
- 环境：OpenHarmony PC（aarch64），clang 15.0.4（OHOS SDK），libc++，C++17
- conan profile：ci/conan/profiles/ohos-aarch64（os=OHOS/arch=armv8/clang15/libc++/cppstd=17/Release）

## 一、上游测试（build() 集成，rule4 N 申报口径）

### N 核验：以实际构建系统注册为准

上游 CTRE 3.11.0 的测试注册口径（实测源码）：

- `tests/CMakeLists.txt`：`file(GLOB test-sources CONFIGURE_DEPENDS *.cpp)` →
  每个 .cpp 注册为 STATIC library 编译目标 `ctre-test-<name>`，归入
  `ctre-test` 自定义 target（MSVC CI 路线：`cmake --build --target ctre-test`）；
- 根 `Makefile`：`TESTS := $(wildcard tests/*.cpp)` → 全部翻译单元编译为
  .o（Linux/macOS CI 路线：`make CXX_STANDARD=17|20`）；benchmark/ 子目录被
  `IGNORE` 与 CMake GLOB（只匹配 tests/ 顶层 `*.cpp`）双重排除。
- **无 Catch2**：任务提示预期"Catch2 vendored"，实测 3.11.0 源码无 Catch2
  依赖（无 .gitmodules、无 third_party/catch、tests/ 无 TEST_CASE 宏）。
  测试形态是**编译期断言**（static_assert 及 TEST_MATCH/TEST_CI_MATCH/
  TEST_SEARCH/TEST_NOT_MATCH/TEST_NOT_SEARCH 宏展开为 static_assert），
  编译成功 = 断言全部成立。

### 申报数字（双口径如实申报）

| 口径 | 数量 |
|---|---|
| 注册编译目标 N（CMake GLOB / Makefile wildcard，tests/*.cpp 全量） | **25** |
| 其中纯编译期断言翻译单元 | 19 |
| 其中含运行期 main 的可执行用例 | 6（cnttp/correct-conversion/is_prime/range/results/wide-pattern） |
| 编译期断言合计（static_assert 1019 + TEST_* 宏用例 133） | 1152 |

### 执行结果（conan create build()，C++17 主口径）

```
PASS __utf8.cpp (compile-time asserts)
PASS _bad_cycle.cpp (compile-time asserts)
PASS _fixed-string.cpp (compile-time asserts)
PASS _unicode.cpp (compile-time asserts)
PASS ci.cpp (compile-time asserts)
PASS cnttp.cpp (runtime) rc=0
PASS correct-conversion.cpp (runtime) rc=0
PASS gcc8.cpp (compile-time asserts)
PASS generating.cpp (compile-time asserts)
PASS gets.cpp (compile-time asserts)
PASS is_prime.cpp (runtime) rc=0
PASS many-of-same-proto.cpp (compile-time asserts)
PASS matching.cpp (compile-time asserts)
PASS matching2-msvc-greedy.cpp (compile-time asserts)
PASS matching2.cpp (compile-time asserts)
PASS matching3.cpp (compile-time asserts)
PASS mode.cpp (compile-time asserts)
PASS msvc.cpp (compile-time asserts)
PASS parsing.cpp (compile-time asserts)
PASS range.cpp (runtime) rc=0
PASS results.cpp (runtime) rc=0
PASS string.cpp (compile-time asserts)
PASS trampoline.cpp (compile-time asserts)
PASS wide-pattern.cpp (runtime) rc=0
PASS z_matching.cpp (compile-time asserts)
TOTAL 25: 25 passed / 0 failed
```

**上游测试用例通过率：25/25（100%）**

补充验证（worktree 外独立实测）：
- C++17 口径 25/25 编译通过（clang 15 -std=c++17 -stdlib=libc++）；
- C++20 口径 25/25 编译通过（-std=c++20，上游 CMake 默认
  CTRE_CXX_STANDARD=20；CTRE 的 tests 均以 `#if CTRE_CNTTP_COMPILER_CHECK`
  双路径编写，OHOS clang 15 C++20 下无失败，无需按"OHOS clang 15 C++20
  支持有限"豁免——实测全过）；
- 0 修改、0 补丁、0 排除（上游测试文件原样编译）。

## 二、test_package（消费者视角，L1）

```
1/1 Test #1: ctre_smoke .......................   Passed    0.04 sec
100% tests passed, 0 tests failed out of 1
All CTRE 3.11.0 smoke tests passed
```

**新增测试用例通过率：1/1（100%）**

test_ctre.cpp 覆盖（R34 实质依赖被测包 API）：
1. C++17 fixed_string NTTP 编译期正则实例化 + static_assert 编译期匹配断言；
2. constexpr 日期提取（官方示例扩展：编译期 optional<date> + 5 个 static_assert）；
3. 运行期 assert：match/search/命名捕获组 get<"name">/search_all 区间迭代/
   starts_with/multiline_match；
4. 包产物 usage 验证：CMakeDeps find_package(compile-time-regular) +
   target_link_libraries(ctre::ctre) 消费者链路。

## 三、包产物验证（header-only）

```
包结构：conaninfo.txt / conanmanifest.txt / include/ (50 个 .hpp) / licenses/LICENSE
库文件（.a/.so）：0
可执行文件：0
bindirs/libdirs：[]（置空）
package_type：header-library（settings 不参与 binary 哈希）
```

## 四、conan create 退出码

```
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... → exit 0
compile-time-regular/3.11.0: Package '6b129b068851896169fae42d399fa922d239ce8a' created
100% tests passed, 0 tests failed out of 1
```
