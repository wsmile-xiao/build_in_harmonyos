# DRAFT-chaiscript-6.1.0-upstream-suite-harness：上游构建不可直用时的等价测试 harness 范式

> Contributor: gcw_6YxinkyD | Status: Draft | Updated: 2026-09-08
> Source: chaiscript 6.1.0 HarmonyOS PC 适配（PR #8935 R51 上游通过率取证）
> 对应：knowledge/drafts/DRAFT-chaiscript-6.1.0-upstream-suite-harness.kv

## 现象

R51（禁占位符）要求 PR 填真实"上游测试用例通过率"，但 chaiscript 上游
CMakeLists：`cmake_minimum_required(2.8)`、对 clang 无条件 `-stdlib=libc++`
（USE_LIBCXX 默认 TRUE）、chai REPL 依赖 readline——无法在 OHOS 工具链下
直接构建跑 ctest。

## 根因分析后的关键事实

1. **上游测试驱动语义完全可复刻**：ctest 对每个 .chai 注册
   `chai unit_test.inc <test>.chai`（独立进程，`exit(-1)` 判失败），断言函数
   （assert_equal 等）由 `unit_test.inc` 定义，宿主只需注册
   exit/quit/throws_exception/get_eval_error/now（src/main.cpp 原样抄）并读
   `CHAI_USE_PATH`/`CHAI_MODULE_PATH`。
2. **catch.hpp 随源码捆绑**（unittests/catch.hpp，Catch v1）：
   "Catch 框架构建期网络下载"是误读——`cmake/Catch.cmake` 只提供
   catch_discover_tests 宏，不下载任何东西。C++ 测试直接编译即可。

## 方案（harness 五要素）

1. **shim 复刻宿主注册面**：40 行 chai_shim 复刻上表五个函数 + 两个路径
   环境变量；
2. **ctest 原语义驱动**：一测试一进程（等价隔离），
   `chai_shim unit_test.inc <test>.chai`；
3. **C++ 测试直编**：上游 10 个测试 .cpp + 捆绑 catch.hpp + static_libs
   两 TU 编进 harness 工程，`find_package(chaiscript)` 以消费者身份链 conan 包；
4. **模块类测试配套**：src/test_module.cpp、stl_extra.cpp（及复测用的
   chaiscript_stdlib_module.cpp）编成 MODULE 放 build 目录供 load_module；
5. **统计口径对齐 ctest 注册数**：.chai 全量（234 + 3.x/ 140）+ TEST_CASE
   计数 + 独立程序数，未执行项写明具体技术原因。

## 验证（真实证据）

真机 OHOS 6.0（clang-15/armv8/libc++）：

- `.chai` 374 个：363 过（11 失败归因见
  DRAFT-chaiscript-6.1.0-cross-dso-typeinfo-identity）
- Catch：48 用例 175 断言全过
- 独立程序：6/7（multithreaded_test 同 RTTI 根因，补建模块复测确认）
- PR #8935 通过率 **417/429（97.2%）**，全部实测无占位符

## 适用边界 / 环境坑

- shim 未复刻 readline 交互与 -c/--version/help 旗标，REPL 交互类 3 个
  ctest 未执行（PR 注明原因）。
- 真机三连坑：`/tmp` 只读 → `TMPDIR` 必须指 `$HOME` 下（否则 clang 报
  "unable to make temporary file"）；`conan install` 无 conanfile 时不能带
  `.` 路径参数（与 `--requires` 冲突直接报错）；生成器落 **cwd 根**而非
  `generators/` 子目录，toolchain 要按 `$PWD/conan_toolchain.cmake` 传。
- 适用画像：嵌入型语言/引擎库（脚本 + 宿主注入断言）或任何"上游 CMake
  不可直用但驱动语义清晰"的库。
