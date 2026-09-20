# veccore 0.8.1 鸿蒙 PC 适配记录（VecCore）

上游：`https://github.com/root-project/veccore`（tag `v0.8.1`，CERN ROOT 项目的
可移植 SIMD 抽象层）。任务 #11637，PR 分支 `feat/veccore-0.8.1`。

## 1. 包形态与关键决策

- **纯头文件**：上游 CMake 目标是 `add_library(VecCore INTERFACE)`，无任何编译
  产物。配方按 `package_type = "header-library"` + `package_id()` 里
  `self.info.clear()` 出包，包内容只有 `include/VecCore/**`（24 个文件，含无扩展名
  的伞形头 `include/VecCore/VecCore`）与 `licenses/LICENSE`。
- **上游测试真跑，不用 test_package 顶替**：`build()` 内 `cmake.configure/build`
  之后执行 `ctest --output-on-failure --output-junit upstream-ctest.xml`，
  用例数由 JUnit 报告解析得到（`tests=`/`failures=`/`errors=`），不是手填。
- **零外部依赖**：GoogleTest 用上游仓库自带的 `builtins/googletest` 快照
  （`-DBUILD_GOOGLETEST=ON`），因此不 require 制品仓的 gtest，也没有 R36 风险。
- **`-DDETAILED_TEST_REPORT=ON` 是取到真实用例数的关键**：默认 OFF 时上游只写
  `add_test(NAME test-backends COMMAND test-backends --gtest_brief=1)`，8 个测试
  文件在 ctest 里只算 1 条。打开后 `gtest_discover_tests` 逐用例注册。
- **`-DINSTALL_GTEST=OFF`**：`add_subdirectory(builtins/googletest
  EXCLUDE_FROM_ALL)` 里的 `EXCLUDE_FROM_ALL` 只管 `all` 目标、不管 install 规则，
  不关掉会把 `libgtest.a`、`libgtest_main.a` 和 gtest 头装进这个 header-only 包。
- **`-DCMAKE_CXX_STANDARD=17` 必须显式传**：上游 `project(VecCore)` 把它写成 11
  （CACHE），而自带快照用了 1.11+ 才有的
  `GTEST_ALLOW_UNINSTANTIATED_PARAMETERIZED_TEST`（需要 C++14 起）；profile 的
  `compiler.cppstd=17` 不会自动覆盖这个 cache 变量。
- **`CMAKE_POLICY_VERSION_MINIMUM=3.5`**：自带 googletest 声明
  `cmake_minimum_required(VERSION 2.8.12)`，真机 CMake 4.4.3 已移除 <3.5 兼容。
- **可选后端全关**（`VC`/`UMESIMD`/`CUDA`/`BUILD_BENCHMARKS`/`BUILD_GOOGLEBENCH`/
  `BUILD_DOCS`）：Vc 与 UME::SIMD 在 aarch64+OHOS 无制品，CUDA 无设备；
  `std::experimental::simd` 后端需要 C++20 且 libc++ 未提供该头，因此本平台的实际
  生效后端是 **Scalar 与 ScalarWrapper**（上游 `test/backends.h` 的无条件部分）。
- **`CMAKE_SYSTEM_NAME` 覆盖**：conan 不写时 CMake 会退回 `uname -s` 的
  `HarmonyOS`，而它只带 `Modules/Platform/OHOS.cmake`，平台变量会全部留空。做法与
  已合入的 vdt 0.4.4 一致（`tc.blocks["generic_system"]`）。
- **无需任何上游源码补丁**：`Common.h` 已有 `__aarch64__ → VECCORE_ARM64` 分支，
  `VecCore/SIMD.h` 的 `<x86intrin.h>` 只在 x86 分支包含，`Utilities.h` 的非 MSVC
  分支用 `posix_memalign`（OHOS musl libc 提供）。`patches_applied: []`。
- `package()` 里 `shutil.rmtree(<pkg>/lib)`：上游会把 `VecCoreConfig.cmake` 与
  `FindUMESIMD.cmake` 装到 `lib/cmake/VecCore/`，与 conan CMakeDeps 给消费方生成的
  同名 config 重名；header-only 包对外只需要 `include/`，`cpp_info` 里
  `bindirs/libdirs/libs` 均置空，对外目标是 `VecCore::VecCore`。

## 2. 用例数口径（审查要求「声明 ≥ 实测」+ 取数命令）

源码声明数（47）：

```sh
grep -cE '(^|[[:space:]])(TYPED_TEST_P|TYPED_TEST|TEST)[[:space:]]*\(' test/*.cc
# align 3 / arithmetics 8 / constructors 6 / interface 15 / limits 1 / mask 11 / math 2 / traits 1 = 47
```

实跑数（581，`ctest` 汇总行 + JUnit `tests=`）：47 个声明是 typed-parameterized
的，按「后端 × 向量类型」展开；本平台的 2 个后端各 290 条，另加上游
`traits.cc` 的 1 条普通 `TEST`：

| 套件 | Scalar | ScalarWrapper |
|---|---|---|
| VectorInterfaceTest | 90 | 90 |
| MaskTest | 66 | 66 |
| ArithmeticsTest | 48 | 48 |
| MathFunctions | 48 | 48 |
| ConstructorTest | 36 | 36 |
| NumericLimitsTest | 2 | 2 |
| **后端小计** | **290** | **290** |

另加上游 `traits.cc` 里 1 条与后端无关的普通 `TEST(TraitTest, TraitTest)`，
合计 **290 + 290 + 1 = 581**。

`align.cc` 的 3 个 `AlignmentTest` 用例在无 Vc / std::simd 后端时按上游设计不实例化
（上游自己写了 `GTEST_ALLOW_UNINSTANTIATED_PARAMETERIZED_TEST(AlignmentTest)`），
本配方没有关掉任何用例、没有排除项、没有跳过项。

## 3. 真机验证记录（HarmonyOS PC，aarch64）

- 设备：真机 `currentUser@127.0.0.1:2200`（经 amax 跳板），HOME
  `/storage/Users/currentUser`，`uname` = HongMeng Kernel 1.12.0 / aarch64。
- **独立缓存**：`CONAN_HOME=/storage/Users/currentUser/work/psj/ch-veccore`
  （全新 home，先 `cp ~/.conan2/profiles/ohos-aarch64` 进去；共享 `~/.conan2`
  只读不动，`global.conf` 未改）。配方目录
  `work/psj/veccore-11637/archives/v/veccore/0.8.1`，日志
  `work/psj/veccore-ch1.log`。
- 命令：

  ```sh
  conan create "$RECIPE" -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
  ```

- 结果（2026-09-20 01:04:23 → 01:08:19 CST，约 4 分钟）：
  - `CREATE_EXIT:0`
  - 取源：`veccore/0.8.1: Sources correctly downloaded from
    https://github.com/root-project/veccore/archive/refs/tags/v0.8.1.tar.gz`
    （13.9MB，sha256 与 `conandata.yml` 一致，亦与本机 `curl` 结果一致）
  - 上游：`100% tests passed out of 581`，`Total Test time (real) = 53.58 sec`
  - 标记：`HMBS_UPSTREAM_TEST_RESULT={"status": "passed", ... "executed": 581,
    "passed": 581, "failed": 0, "skipped": 0}`
  - test_package：`veccore consumer probe: 90 checks, 0 failures -> PASSED`、
    `veccore OHOS probe: __OHOS__=1 arm_path=1 x86_path=0 simd_align=16` +
    `18 checks, 0 failures -> PASSED`
  - 配方 rev `b777b9254df1cc067964be773c93fbaf`、包 ID
    `da39a3ee5e6b4b0d3255bfef95601890afd80709`（header-only `info.clear()` 的固定
    ID）、包 rev `f03cffc3b913e41d516318a6f7e6eb2e`
  - 包内容：`include/VecCore/**` 24 个文件 + `licenses/LICENSE`，无 `lib/`
- 证据链：上传走 base64 打包 + 设备解码，5 个 conan 输入文件
  （`conanfile.py`、`conandata.yml`、`test_package/{conanfile.py,consumer.cpp,
  test_veccore_ohos.cpp}`）在推送前后设备侧 md5 与本地逐字节相同
  （`31592f46… / 0690b775… / f667b284… / 15243a95… / 921a9085…`），
  即「真机跑的配方 == 推上去的配方」。

## 4. 边界

- 本包不提供 x86 SIMD 后端；在 aarch64/OHOS 上 VecCore 走标量路径，价值在于
  让上层 SIMD 抽象代码能在鸿蒙上编译、运行并保持可移植性（这也是上游 README 对
  不支持架构的官方说法）。
- 若将来需要 `std::experimental::simd` 后端，需要 C++20 与提供该头的标准库，
  当前 profile（clang 15 + libc++，cppstd=17）不具备。
- 消费者测试为静态头文件消费，无 `.so`，因此不涉及 E077 重签流程。
