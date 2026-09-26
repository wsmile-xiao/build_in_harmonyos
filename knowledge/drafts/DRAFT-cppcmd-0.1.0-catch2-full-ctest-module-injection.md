# DRAFT: Conan 版 Catch2 包缺 contrib/Catch.cmake 时，注入完整上游 Catch.cmake + CatchAddTests.cmake 保留下游逐用例 CTest 注册

> 来源: cppcmd 0.1.0 HarmonyOS PC 适配（header-only C++ 命令解释器库, task cppcmd-0.1.0-r01-pc4-22）
> 状态: 草稿 (draft) — 与 DRAFT-cppcmd-0.1.0-catch2-full-ctest-module-injection.kv 配对
> 关联: DRAFT-ctpg-1.3.7-catch2-ctest-module-injection（最小 shim 方案，同触发面）、
>       DRAFT-cdt-1.4.5-catch2-21310-amalgamated-test-adaptation（v2.13 包不透出 Catch.cmake 同根因）

## 问题

上游 `tests/CMakeLists.txt` 标准写法（cppcmd 0.1.0 即此形态）：

```cmake
find_package(Catch2 REQUIRED)
include(Catch)
add_executable(cppcmd-test test_main.cpp)
target_link_libraries(cppcmd-test cppcmd Catch2::Catch2)
catch_discover_tests(cppcmd-test)
```

Conan 环境（ohpcd catch2/2.13.10 header-only 包）下配置失败：

```text
CMake Error at tests/CMakeLists.txt:4 (include):
  include could not find requested file: Catch
CMake Error at tests/CMakeLists.txt:13 (catch_discover_tests):
  Unknown CMake command "catch_discover_tests"
```

## 根因

Catch2 2.x 把逐用例 CTest 注册宏 `catch_discover_tests` 放在框架安装目录的
contrib 模块（`Catch.cmake` + 运行期辅助脚本 `CatchAddTests.cmake`）中。
ohpcd 制品仓的 catch2/2.13.10 header-only 包只复制 `single_include/catch2` 头文件，
不含 contrib 模块；CMakeDeps 提供 Catch2Config.cmake / Catch2::Catch2 target
（find_package 命中），但 `include(Catch)` 找不到模块、`catch_discover_tests`
是未知命令 —— "测试框架包已发布"与"CTest 集成模块缺失"同时成立。

## 与本仓库既有草稿的差异（新增差异）

- **DRAFT-ctpg-1.3.7-catch2-ctest-module-injection**：注入**最小** shim
  （`function(catch_discover_tests TARGET) add_test(NAME ${TARGET} COMMAND ${TARGET}) endfunction()`），
  把整个测试二进制注册为**单个** ctest 用例；Catch2 内部 TEST_CASE 细分粒度
  （ctest -N 看不到每个用例）丢失，对双口径台账的「源码声明 → ctest 注册项」
  逐项映射支撑不足。
- **本轮方案（完整上游模块注入）**：直接取 Catch2 v2.13.10 官方
  `contrib/Catch.cmake`（206 行）+ `contrib/CatchAddTests.cmake`（135 行）放入
  构建目录并设置 CMAKE_MODULE_PATH，`catch_discover_tests` 按上游语义把
  TEMPLATE_LIST_TEST_CASE 各类型实例与 TEST_CASE 逐项注册进 CTest ——
  本轮 ctest -N 显示 6 个独立用例（Expression parsing ×3 模板实例 +
  Argument parser + Registering commands + More CommandInterpreter instances），
  与源码声明逐一对应，双口径台账可直接映射。

## 方案

```bash
# 构建环境（探索构建目录 build-native/ 下放置）：
curl -sS --resolve raw.githubusercontent.com:443:185.199.108.133 \
  -o build-native/Catch.cmake \
  https://raw.githubusercontent.com/catchorg/Catch2/v2.13.10/contrib/Catch.cmake
curl -sS --resolve raw.githubusercontent.com:443:185.199.108.133 \
  -o build-native/CatchAddTests.cmake \
  https://raw.githubusercontent.com/catchorg/Catch2/v2.13.10/contrib/CatchAddTests.cmake
# CMake 配置时指定模块路径：
cmake -S . -B build-native -DCMAKE_MODULE_PATH=$(pwd)/build-native ...
```

注意：两个文件必须配套（Catch.cmake 内 `CatchAddTests.cmake` 由
`catch_discover_tests` 生成 build-time 调用脚本，缺失时报 "Not a file:
.../CatchAddTests.cmake"）。模块文件属本地构建支持物，**不入配方、不入 PR**。

## 验证

- ctest 6/6 Passed，120 assertions；`catch_discover_tests` 逐用例注册成功
  （ctest -N 显示 6 个用例，含 TEMPLATE_LIST_TEST_CASE 的 3 个类型实例化）。
- 日志: /storage/Users/currentUser/tmp/cppcmd-0.1.0-logs/upstream-ctest.log
  SHA-256 3550645a4bdc142ba72559cf489c15457be7ace877d04a7147c786caedb48951

## 适用边界 / 反例

- 适用: 上游 tests/CMakeLists.txt 用 include(Catch) + catch_discover_tests 的
  Catch2 2.x 库；Conan 版 catch2 包缺 contrib 模块；需要 ctest -N 逐用例粒度
  支撑测试台账的适配任务。
- 反例: 上游直接 `add_test(NAME t COMMAND t)` 注册时无需该模块；Catch2 v3
  多头 include 布局走 DRAFT-cdt 场景（amalgamated 包适配）；对测试仅需
  二进制级通过/失败、不做逐用例台账的库，用最小 shim（DRAFT-ctpg）已足够。
- 注: 本方案是探索构建期的构建环境支持物，不进入 conanfile.py/test_package
  交付；若需在 conan create 内保留上游测试逐用例注册，可参考 DRAFT-ctpg 在
  generate() 注入模块的路径把完整模块一并注入（待后续库验证后扩展）。
