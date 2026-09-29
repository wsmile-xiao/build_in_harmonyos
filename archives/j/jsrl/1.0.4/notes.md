# jsrl 1.0.4 适配笔记

## 编译环境
- 构建系统: cmake（上游 `cmake_minimum_required(VERSION 3.14...3.27)`；manifest `build.system: cmake`）
- 编译日期: 2026-09-28
- 编译器: clang/clang++ 15.0.4（`aarch64-unknown-linux-ohos`，HNP 工具链），libc++；
  Conan profile `ci/conan/profiles/ohos-aarch64`（os=OHOS/6.0、arch=armv8、
  compiler.version=15、compiler.libcxx=libc++、compiler.cppstd=17、build_type=Release）
- 编译标准: **C++17** —— 库本体与测试树与上游 CI 同口径（上游不传 `CMAKE_CXX_STANDARD`，
  根 CMakeLists 回落 17）；test_package 消费面同为 17（验证声明下限）
- 并行度: `tools.build:jobs=4`（配方 `generate()` 内 define；cpu_count=20 / affinity=8，
  不钉会 2.5× 超订，device-facts §一.7）
- 状态: built（O5：合并并确认 release upload 之前一律 built）

## 编译步骤

1. 源码三路取证（W0-1）：`git ls-remote --tags https://github.com/adobe/jsrl` → 5 个 tag
   全量命中，`1.0.4`（**无 v 前缀**）= `2868f64f0f66b993a161bd91b2cb747933c0b54a`；
   官方 tag 归档实测 sha256 = `6d530713ba00f8c762f55393c96c14a0d6eb9b6f8744aa87125e63af88ff1885`
   （63 976 B，解包 564 K）== task-scout 归档副本 == CCI 归档配方记录值，三路逐字一致。
2. Conan 配方构建（CI 同路径）：
   ```bash
   conan create archives/j/jsrl/1.0.4 \
     -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
   ```
   配方内部：`generate()`（CMakeToolchain 钉 `JSRL_BUILD_TESTS=ON` / `JSRL_INSTALL=ON` /
   `BUILD_SHARED_LIBS=OFF` + `GTest_DIR` 指向 gtest 包自带 config + `tools.build:jobs=4`）
   → `cmake.configure()` → `cmake.build()` → **层 1 上游测试**（四重反假绿断言 + 沙箱 HOME
   下 `ctest --test-dir <build> --output-on-failure -V`）→ `package()`（`cmake --install` +
   LICENSE + 删除上游自带 config/pc + 安装树清点 6 头 / 1 库）→ `test_package/` 消费者 9 断言。
3. 消费者层：`test_package/` 经 CMakeDeps 的 `jsrl::jsrl` 链接打包产物，以**声明的最低标准
   C++17** 编译并运行 9 条断言，末行 `JSRL-CONSUMER checks=9 failures=0`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 任务卡写「0 依赖」，但上游测试要 GoogleTest | 上游 `tests/CMakeLists.txt` 顶层 `find_package(GTest)`，找不到就 FetchContent 拉 googletest v1.14.0（**构建期联网**，CI 侧不可靠） | 按实有依赖登记为**测试期依赖** `self.test_requires("gtest/1.17.0")`（`conan download … -r=ohpcd` rc=0、同 profile binary 可得）；库本体 `requirements()` 保持为空，依赖不传播给消费者；`manifest.build.dependencies: []` + `test_dependencies: [gtest/1.17.0]` 两栏分列 |
| 2 | `jsrl_format_test`（36 例）在 OHOS 编不过 | 上游 `tests/CMakeLists.txt:46` 只在 `CMAKE_CXX_STANDARD >= 20` 才编该测试；上游 CI 不传该变量 ⇒ **上游 CI 同样不编**。本机即使抬到 C++20 也编不过，三步实测：①libc++15 `<format>` 被平台配置整体禁用（`<libcxx-ohos>/include/c++/v1/__config:255` `#define _LIBCPP_HAS_NO_INCOMPLETE_FORMAT`，`__has_include(<format>)` 为真但 `std::format`/`std::formatter` 未定义）；②强开 `-D_LIBCPP_ENABLE_EXPERIMENTAL` → **链接失败** `undefined symbol: typeinfo for std::__n1::format_error` / `~format_error()`（OHOS libc++.so 未编入 format 支持）；③自补析构后**编译失败 17 处**（libc++ `__formattable` 概念形参按值取 `T`，而 `jsrl::Json::Error` 是抽象类，`jsrl.hpp:900` `~Error() noexcept override = 0` ⇒ `call to deleted function '__determine_arg_t<…, jsrl::Json::Error>'`，`format_arg_store.h:157/158/163/166` 连环常量表达式失败） | 按 §3.5「OHOS 缺特性」把 36 例申报为 **NOT_RUN**（既非 PASS 也非 SKIP，不进通过率分子），取数口径与三步证据写进 `conanfile.py` docstring、`test_package/MANIFEST.yml` 与 `reports/test-report.md`；**不删测试、不改上游测试、不写假 PASS**。配方另加硬断言 `tests/jsrl_format_test` 必须**不存在**，上游若翻转该门会立刻失败暴露而不是静默少跑 |
| 3 | 上游 `find_package(GTest)` 拿不到 `GTest::gtest` 目标 | conan `gtest/1.17.0` 自身导出的 `cmake_file_name/target_name` 是小写 `gtest`/`gtest::gtest`，而上游测试树要 `GTest::gtest`/`GTest::gtest_main`；同时 CMake 自带 FindGTest 模块在 OHOS 上找不到包 | 走 **gtest 包自带**的 `lib/cmake/GTest/GTestConfig.cmake`：`CMakeDeps.set_property("gtest","cmake_find_mode","none")` 关掉再生成 + `tc.cache_variables["GTest_DIR"]` 指向包内目录（abseil / cpp-httplib / benchmark 同款走法），零源码补丁 |
| 4 | `pretty_print` 找不到 | 它在 `jsrlpp.hpp`，`jsrl.hpp` 并不 include 它（README 示例用 `using namespace jsrl` 且同时可见两个头） | 消费者 `#include <jsrl/jsrl.hpp>` 之外再加 `#include <jsrl/jsrlpp.hpp>`（包内已安装该头，顺带验证安装树完整） |
| 5 | 高保真数字断言首版写 30 位小数不过 | 默认解析路径会丢**末尾无意义的 0**（`…67890` → `…6789`），数值本身无损；`use_GN_for_floats` 只改记法（科学计数）不改值 | 断言改用**无尾零**的 29 位小数 `1234567890.1234567890123456789` + 双精度不可表示的整数 `9007199254740993`（2^53+1，double 会读成 …992），两者逐字保留 ⇒ 断言面更严格且稳定 |

## 源码修改

**无。** `conandata.yml` 的 `patches: {}`，零补丁 —— W0-3 四组 grep（ISA 专属头、glibc printf
钩子族、架构可移植性档、架构/平台条件编译宏）在全仓各 **0 命中**（证据：
`$TASK_DIR/w0-evidence.md`），所有适配都在配方侧完成。

## 依赖版本

- 运行/编译依赖：**无**（任务卡「0 依赖」实核成立）
- 测试期依赖：`gtest/1.17.0`（`test_requires`，不进包依赖链、不传播给消费者）
- 工具链：clang 15.0.4 / cmake 4.1.2 / conan 2.29.1（均来自 profile 与 HNP）

## 验证结果

上游测试台账（R51 三步法，单位＝gtest 用例；取数命令见 `test_package/MANIFEST.yml`）：

| 口径 | 值 | 取数命令 |
|---|---|---|
| ① 源码宏数（**N，候选最大值**） | **148** | `grep -hoE '^\s*(TEST\|TEST_F\|TEST_P)\s*\(' <src>/tests/*.cpp \| wc -l`（上游当前 HEAD ce9cec7 同值） |
| ② 框架注册数（＝实跑 N′） | **112** | 4 个二进制 `--gtest_list_tests` 缩进行求和（5+43+53+11）；`ctest -N` → Total Tests: 4 |
| ③ assertion 数（单列不作 N） | 950 | `grep -hoE '\b(EXPECT\|ASSERT)_[A-Z_]+' <src>/tests/*.cpp \| wc -l` |
| ④ 消费者断言数（鸿蒙特有，不进分母） | 9 | `./test_jsrl` → `JSRL-CONSUMER checks=9 failures=0` |

`TOTAL = PASS + FAIL + SKIP + NOT_RUN = 112 + 0 + 0 + 36 = 148 = N`，通过率 **112/148（75.68%）**；
分栏口径：框架口径 112/112 全过、CTest 程序口径 4/4 全过。36 例 NOT_RUN 的逐条归因见问题 2。

- `conan create`（CI 同路径）rc=0；配方内 `[upstream-tests]` 台账行逐字可核：
  `ctest 注册项 = 4`、`框架注册数合计 = 112`、`ctest rc=0 全过判定=是 [PASSED] 求和=112`、
  `[package] 头文件清点=6 件、库=lib/libjsrl.a`。
- 消费者：`JSRL-CONSUMER checks=9 failures=0`。

## 注意事项

- `jsrl_format_test` 的 36 例为 **NOT_RUN**（平台缺 `std::format` + 上游 C++20 门），
  声明 N=148、实跑 N′=112，读 PR 时请连同归因段一起读，勿把 NOT_RUN 当 PASS。
- 本包为 `upstream/main` 首次出现的**全新包目录**（`--allow-unpublished` 放行），
  分支名门禁按 `jsrl-1.0.4` == 包目录名-版本 匹配。
