# boost-ext-ut 2.3.1 适配笔记

## 基本信息
- **上游**: https://github.com/boost-ext/ut
- **版本**: 2.3.1（tag v2.3.1）
- **任务分支**: feat/boost-ext-ut-2.3.1
- **许可证**: BSL-1.0 (Boost Software License)
- **类型**: header-only C++20 微型单元测试框架（`include/boost/ut.hpp` 3378 行完整实现；`ut.cppm` 仅为 C++23 模块包装）
- **依赖**: 无（上游测试套件全部离线，无 FetchContent）

## 构建系统
CMake（另有 meson.build，未使用）。配方 `generate()` 关键变量：
- `BOOST_UT_DISABLE_MODULE=ON`：纯头模式（模块模式需 CMake ≥ 4.0 + C++23，OHOS 工具链不适用）
- `BOOST_UT_ENABLE_RUN_AFTER_BUILD=OFF`：见下"踩坑 1"，与上游全部 CI 工作流一致
- `BOOST_UT_BUILD_TESTS=ON` + `BOOST_UT_BUILD_EXAMPLES=ON`：上游测试与示例全部构建
- `BOOST_UT_BUILD_BENCHMARKS=OFF`、`BOOST_UT_ENABLE_INSTALL=OFF`（`package()` 直接 copy 头文件与 LICENSE）
- `BOOST_UT_USE_WARNINGS_AS_ERORS=OFF`：不把 clang 15 的警告升级为错误（不改变任何测试逻辑）
- C++ 标准：profile `compiler.cppstd=17`，配方 `configure()` 中 `rm_safe("compiler.cppstd")`（header-only 包兼容性与 cppstd 无关）；上游 `target_compile_features(ut INTERFACE cxx_std_20)` 使所有链接 `Boost::ut` 的目标按 C++20 编译，消费者 test_package 亦显式 `target_compile_features(... cxx_std_20)`

## 安装产物
- 头文件: `include/boost/ut.hpp`
- 许可证: `licenses/LICENSE.md`
- CMake: `find_package(ut)` → 目标 `Boost::ut`（与上游 utConfig.cmake 命名一致）

## 踩坑与解决
1. **Error 127 `/bin/sh: boost_ut_runner: inaccessible or not found`**：上游 `cmake/AddCustomCommandOrTest.cmake` 的 `BOOST_UT_ENABLE_RUN_AFTER_BUILD` 默认 ON，POST_BUILD 用裸命令名运行刚构建的可执行文件，POSIX sh 不搜索当前目录。上游所有 CI 工作流（linux/macos/windows/emscripten/install）均传 `-DBOOST_UT_ENABLE_RUN_AFTER_BUILD=NO` 改走 `add_test`；配方同样设置，由 `cmake.test()` 运行 ctest。
2. **`example/parameterized.cpp:50: no member named 'views' in namespace 'std'`**：OHOS clang 15 的 libc++ 定义 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES`，`std::views` 不存在（探针实证；`__cpp_lib_ranges` 却已定义，不能用它判断）。对全部 41 个 example 与 test 源做 `-fsyntax-only` 扫描，仅此 1 处受影响。补丁见下。
3. **test_package `given/when/then` 未声明**：boost.ut 的 BDD DSL 位于 `boost::ut::bdd`，需单独 `using namespace boost::ut::bdd;`（上游 `example/BDD.cpp` 同款）。

## 补丁
- `patches/0001-example-parameterized-guard-std-views-for-incomplete-ranges.patch`（portability，1 行）
  - 文件：`example/parameterized.cpp`
  - 原因：libc++ 17 之前 ranges 不完整，`std::views::iota` 不可用（OHOS clang 15 编译失败）
  - 内容：把上游同文件已有的 `#ifndef __EMSCRIPTEN__` 守卫扩展为 `#if !defined(__EMSCRIPTEN__) && !defined(_LIBCPP_HAS_NO_INCOMPLETE_RANGES)`；未引入任何平台宏（R8/PF5 合规），libc++ ranges 完整后该子测试自动恢复
  - 影响：仅该示例中 1 个 `"views"_test` 子测试在 libc++ < 17 下不编译；示例其余子测试与其他 40 个示例不受影响
  - 验证：`git apply --check` 通过；打补丁后 conan create 全部 example 编译成功

## 上游测试统计（四类数字口径）

1. **上游静态注册点: 46**（全部经 `ut_add_custom_command_or_test()` → `add_test` 注册）
   - `test/ut/CMakeLists.txt`: `ut(ut)` + `ut(win_compat_test)`（仅 WIN32）= 2
   - `test/ft/CMakeLists.txt`: `ft` / `ft-no-exceptions`（-fno-exceptions）/ `ft-link`（多 TU 链接，非 WIN32）= 3
   - `example/CMakeLists.txt`: `example(...)` 41 处
   - 补充：`test/ut/ut.cpp`（2065 行）内部约 41 个 ut 用例，属框架自测，归入 `ut_test` 单个 ctest 条目
2. **官方套件实际执行: ctest 4/4 通过**——`ut_test`、`ft`、`ft-no-exceptions`、`ft-link`（`100% tests passed, 0 tests failed out of 4`）
   - 41 个 example 全部编译验证通过（`BOOST_UT_BUILD_EXAMPLES=ON`）
3. **未执行/未注册说明**
   - `win_compat_test`：WIN32-only，平台条件不构建
   - examples 不进入 ctest：上游根 CMakeLists 的 `enable_testing()` 位于 `add_subdirectory(example)` 之后，example 目录内 `add_test` 不生效；上游全部 CI 工作流均以 `RUN_AFTER_BUILD=NO` 运行 ctest，因此上游官方 ctest 口径同样是 test/ 目录的 4 项。本适配与上游 linux CI 完全一致，未删除任何测试
4. **新增 test_package 消费者测试: 2 个程序**
   - `test_boost_ext_ut.cpp`（C++20）：用 boost.ut 自身编写 6 个测试块（算术/字符串/sections/BDD/参数化 ×4 值/异常）共 15 个 `expect`；运行时 runner 报 `all tests passed (21 asserts in 14 tests)`（sections/BDD/参数化按 ut 语义展开计数），要求退出码 0
   - `test_boost_ext_ut_negative.cpp`：含 2 个 `expect`（1 个通过 + 1 个故意失败的 `expect(1_i == 2)`），runner 输出 `FAILED ... [1 == 2]` 并以非 0 退出；`test()` 以 `&& exit 1 || exit 0` 反转判定，证明运行器真实评估断言而非恒返回 0
   - 源码合计 17 个 expect（15 + 2），全部按预期

## OHOS 适配
- E092：`CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR`（`settings.os in ("Linux", "OHOS")`）
- `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`
- 本机（aarch64 鸿蒙）conan create 时 `can_run` 为真，上游 ctest 与消费者测试均真实执行

## 验证命令
```bash
export CONAN_HOME="$HOME/tmp/ch/home-boost-ext-ut"
export SSL_CERT_FILE="$HOME/usr/local/ssl/cert.pem"
python3 scripts/ohc-run.py conan-verify boost-ext-ut 2.3.1
# conan create: -pr:h/-pr:b ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```
- conan-verify 报告: `reports/conan-verify-report.md`（G0-G4 + L2/L4/L5 全 PASS）
- W3 本地 CI 日志: `reports/w3-local-ci.log`
