# DRAFT: 上游测试目录配置期 file(DOWNLOAD) 拉取 conan.cmake 网络阻塞 → 用 registry catch2 头文件直接编译运行上游测试源

> 来源: bertrand 0.013 HarmonyOS PC (arm64) 适配（header-only 设计契约库）
> 状态: 草稿 (draft) — 与 DRAFT-bertrand-0.013-conan-cmake-download-bypass-direct-compile.kv 配对
> 关联: archives/b/bertrand/0.013/reports/knowledge-candidate-ledger.md (C1/C3)

## 问题

bertrand 0.013 的上游测试子目录 `test/CMakeLists.txt` 使用 cmake-conan 集成：

```cmake
if(NOT EXISTS "${CMAKE_CURRENT_BINARY_DIR}/conan.cmake")
  file(DOWNLOAD
    "https://raw.githubusercontent.com/conan-io/cmake-conan/v0.15/conan.cmake"
    "${CMAKE_CURRENT_BINARY_DIR}/conan.cmake")
endif()
include(${CMAKE_CURRENT_BINARY_DIR}/conan.cmake)
conan_cmake_run(CONANFILE conanfile.txt BASIC_SETUP CMAKE_TARGETS BUILD missing)
find_package(Catch2 REQUIRED)
add_executable(bertrand_tests src/Catch2Main.cc src/text_tests.cc ...)
```

执行端网络策略不放开 `raw.githubusercontent.com`，`-DBUILD_TESTING=ON` 配置时
configure 在 "Downloading conan.cmake …" 处无限挂起（实测 180s 截获）。上游
测试入口整体被封锁，但不是库源码缺陷。

## 根因

测试引导机制（cmake-conan）依赖外网下载；执行端外网受限时配置期即卡死，CTest
入口不可达。

## 方案（registry-header-direct-compile）

1. 不改上游 CMakeLists、不动测试源码、不打补丁；
2. 从 ohpcd registry 安装可得版本 `catch2/2.13.10`
   （上游声明的 2.13.1 精确版本 registry 不可得——两次下载均返回
   acceleration policy 错误；2.13.x 同系列 API 兼容，属版本兼容复查）；

```bash
conan install --requires=catch2/2.13.10 -r=ohpcd \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing -of=<catch2-install>
```

3. 按上游 add_executable 的真实源清单，用 OHOS 工具链 clang++ 直接编译运行
   （含上游同款业务宏：BERTRAND_ENABLE_CONTRACTS / BERTRAND_CONTRACTS_ARE_EXCEPTIONS，
   与上游 CMakeLists 中 GNU/Clang 分支的编译选项一致）：

```bash
clang++ -std=c++17 -I include -I <catch2>/include \
  -DBERTRAND_ENABLE_CONTRACTS -DBERTRAND_CONTRACTS_ARE_EXCEPTIONS \
  -Wall -Werror -pedantic \
  test/src/Catch2Main.cc test/src/bertrand_tests.cc \
  test/src/in_operator_tests.cc test/src/text_tests.cc -o bertrand_tests
./bertrand_tests
```

结果: `All tests passed (18 assertions in 16 test cases)`，exit 0。

## 验证

- 编译 exit 0 / 运行 exit 0（日志 upstream-tests-compile.log / upstream-tests-run.log）
- failing_contract 五模式行为全部符合上游预期（Debug 违约 SIGABRT=134 / Release=0 /
  强制开关 / 双标志编译拦截）
- 与上游测试声明逐项核对：16 个 Catch2 TEST_CASE 全枚举全运行（台账双口径
  source_declared_total=31，可执行集合 17/17=100%）

## 适用边界 / 反例

- 适用：上游测试目录配置期 file(DOWNLOAD) 下载 conan.cmake、执行端外网受限、
  Catch2 2.x 单头/合并头布局（可直接 -I 编译）。
- 反例：上游测试依赖 framework 二进制符号或多头布局且 registry 仅有不兼容版本
  → 需头布局适配（见 cdt 草稿）或 Catch.cmake 模块注入（见 ctpg 草稿）；
  此时不适用本方案。
- 宏门控 header-only 库（C3 要点）：test_package 消费者测试中使契约/特性宏
  必须在 include 前生效——用 target_compile_definitions 传入（同上游测试编译
  选项），不要在源码内 include 之后 #define（否则头文件在 include 时判定宏
  未开，API 不可见，报 undeclared identifier）。

## 查重差异

- 与 DRAFT-ctpg-1.3.7-catch2-ctest-module-injection 不同：ctpg 是配置期
  `include(Catch)/catch_discover_tests` 缺 Catch.cmake 模块（打包不完整）需注入
  模块；本候选是配置期外网下载 conan.cmake 阻塞，方案为绕开引导直接编译。
- 与 DRAFT-cdt-1.4.5-catch2-21310-amalgamated-test-adaptation 不同：cdt 是 Catch2
  v3 多头头在制品仓 v2.13 合并头布局下缺失需头适配；本候选上游即 v2 单头
  布局，registry 2.13.10 直接可用，零源码修改。
- 与 DRAFT-kangaru-4.3.2-catch2-submodule-test-requires 不同：kangaru 是源码包
  submodule 空目录需 conan test_requires；本候选无 submodule 问题。

## 关系

similar_to: DRAFT-ctpg-1.3.7-catch2-ctest-module-injection,
DRAFT-cdt-1.4.5-catch2-21310-amalgamated-test-adaptation,
DRAFT-kangaru-4.3.2-catch2-submodule-test-requires,
DRAFT-ctre-3.10.0-header-only-recipe-test-package