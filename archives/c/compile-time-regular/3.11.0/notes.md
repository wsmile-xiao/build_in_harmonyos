# compile-time-regular 3.11.0 编译笔记

## 任务背景

- **任务**：积分赛 #6568 — compile-time-regular（CTRE）3.11.0 适配
- **认领人**：2404_87638649
- **平台分支**：feat/compile-time-regular-3.11.0
- **样板**：boost1.84-contract（header-only 组件包先例，archives/b/boost1.84-contract/）
- **开始时间**：2026-09-07

## 开工前四维核验（2026-09-07 实测）

1. **制品仓**：`conan.cnb.cool .../conans/search?q=compile-time*` → `{"results":[]}`
   （q=compile / q=ctre 均空）→ 无任何版本，3.11.0 不存在 ✓
2. **仓库 main**：`git ls-tree origin/main archives/c/` → 无 compile-time-regular
   （只有 compiledb 等无关包）→ 无历史实现 ✓
3. **上游 tag**：`https://cdn.jsdelivr.net/gh/hanickadot/compile-time-regular-expressions@3.11.0/`
   → HTTP 200，文件清单完整（include/ 53 头文件 + tests/ + single-header/）✓
4. **平台任务**：`GET /api/contrib/tasks?search=compile-time` → id=6568，
   claimer=2404_87638649，taskBranch=feat/compile-time-regular-3.11.0，
   status=assigned ✓

## 库特性与形态选型

CTRE 是 header-only C++17 编译期正则库：

- **零依赖**：无 requirements（无 boost/无任何 conan 依赖），W0 检查天然通过
- **纯 header 交付**：package() 只拷贝 include/*.hpp + LICENSE，参照
  boost1.84-contract 样板（package_type="header-library" + no_copy_source）
- **产物**：include/{ctre.hpp, ctll.hpp, ctre-unicode.hpp, unicode-db.hpp,
  ctre/, ctll/, unicode-db/}，bindirs/libdirs 置空

## 上游 N 核验（rule4 纪律：以实际构建系统注册为准）

### 任务预期 vs 实测

任务描述预期"Catch2 vendored 自带"——**实测 3.11.0 源码无 Catch2**：

- tests/CMakeLists.txt：`file(GLOB test-sources CONFIGURE_DEPENDS *.cpp)` →
  每个 .cpp 注册为一个 STATIC library 编译目标（ctre-test-<name>），归入
  ctre-test 自定义 target；
- Makefile：`TESTS := $(wildcard tests/*.cpp)` → 每个翻译单元编译为 .o，
  上游 CI（.github/workflows/tests.yml）`make CXX_STANDARD=17|20` 只编译不链接
  （benchmark-exec 除外，被 IGNORE 排除）；
- **测试形态是编译期断言**（static_assert / TEST_MATCH 等宏展开为
  static_assert），编译成功 = 断言全部成立；无 Catch2 TEST_CASE、无 ctest 注册。

### N 申报口径（双数字如实申报）

- **注册编译目标 N = 25**（tests/ 顶层 .cpp 全量，benchmark/ 子目录被上游
  Makefile IGNORE 与 CMake GLOB `*.cpp` 双重排除）；
- 其中 21 个为纯编译期断言翻译单元（static_assert 1019 个 + TEST_* 宏
  展开 133 个 = **编译期断言合计 1152**），4+2 个含运行期 main（cnttp/
  correct-conversion/is_prime/range/results/wide-pattern 共 6 个可执行程序）。

### 本地实测（OHOS clang 15 + libc++，2026-09-07）

```bash
# C++17（CI profile 口径）
for f in tests/*.cpp; do clang++ -std=c++17 -stdlib=libc++ -Iinclude -c $f; done
# → 25/25 编译通过（0 修改 0 补丁 0 排除）

# C++20（上游 CMake 默认 CTRE_CXX_STANDARD=20）
# → 25/25 编译通过

# 6 个运行期用例链接运行（-static-libstdc++）
# → cnttp/correct-conversion/is_prime/range/results/wide-pattern 退出码全 0
```

## 关键坑与决策

### 1. C++17 下字符串字面量 NTTP 不可用（官方路径已内置）

`ctre::match<"[0-9]+">("12345")` 的字符串字面量模板参数是 C++20 特性
（clang 15 在 C++17 报 `reference to string literal is not allowed in a
template argument`）。CTRE 官方通过 `CTRE_CNTTP_COMPILER_CHECK` 宏自动探测：

- C++20：CNTTP 路径（`ctre::match<"...">` 直接可用）；
- C++17：`ctll::fixed_string` NTTP 路径（`static constexpr auto pattern =
  ctll::fixed_string("[0-9]+"); ctre::match<pattern>(...)`）——上游测试
  全部用 `#if CTRE_CNTTP_COMPILER_CHECK` 双路径编写，C++17 下自动走
  fixed_string 仿真路径。

本包 test_package 按 C++17 口径（profile cppstd=17）用 fixed_string 路径
验证（test_ctre.cpp），同时 C++20 路径在上游 tests/ 全量编译中已覆盖。

### 2. libc++_shared.so 运行时缺失（样板同坑）

测试二进制动态链接 libc++_shared.so 时报 `Error loading shared library
libc++_shared.so`。解法与 boost1.84-contract 样板一致：`-static-libstdc++`
静态链接 C++ 运行时。

### 3. 上游 tag 带 v 前缀

GitHub tag 名为 `v3.11.0`，codeload 归档 URL
`.../refs/tags/v3.11.0.tar.gz`，解开后目录名
`compile-time-regular-expressions-3.11.0`（无 v）——conandata.yml 用
strip_root 处理。注意：**不带 v 的 .../3.11.0.tar.gz 会 404**。

### 4. license 表述

上游 LICENSE 文件为 Apache 2.0 + LLVM Exception 双许可，SPDX 规范写法
`Apache-2.0 WITH LLVM-exception`。

## W0 依赖检查（R36）

无依赖（header-only 零依赖库），无需 conan download 验证。

## 验证结论

- conan create（header-only）：include/ 头文件交付 + test_package 编译期
  实例化验证全绿（详见 reports/）；
- 上游 tests/ 25 目标全量编译（C++17 主口径）+ 6 运行期用例实际运行全 0 退出码；
- 测试策略说明：上游测试本质是编译期断言，能编译即验证；运行期用例真跑。
