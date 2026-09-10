# cpptrace 1.0.4 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，CMake >= 3.15）
- 编译日期: 2026-09-09
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos 目标）/ libc++ / C++17
- 状态: built（本地 conan create + 上游测试 + test_package 全部通过；尚未 release upload）

## 编译步骤

1. 源码包：https://github.com/jeremy-rifkin/cpptrace/archive/refs/tags/v1.0.4.tar.gz
   （注意 tag 带 `v` 前缀，与 conandata.yml 的 URL 一致）
2. 语言预检：C++（cpptrace.hpp + src/*.cpp，纯 C++ 项目）
3. Conan 配方构建：
   `conan create archives/c/cpptrace/1.0.4 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`
4. CMake 配置由 CMakeToolchain 生成，核心开关：
   - `CMAKE_SYSTEM_NAME=Linux`（见问题 1）
   - `CPPTRACE_CONAN=ON` + `CPPTRACE_USE_EXTERNAL_LIBDWARF=ON` + `CPPTRACE_USE_EXTERNAL_ZSTD=ON`
   - `CPPTRACE_USE_EXTERNAL_GTEST=ON` + `GTest_DIR=<conan gtest 包>/lib/cmake/GTest`
   - `CPPTRACE_UNWIND_WITH_UNWIND=ON` + `CPPTRACE_GET_SYMBOLS_WITH_LIBDWARF=ON` + `CPPTRACE_DEMANGLE_WITH_CXXABI=ON`
   - `CPPTRACE_BUILD_TESTING=ON`（上游测试在 build() 内构建并运行）
5. 上游测试（build() 内执行）：unittest 155 用例（158 声明中非 MSVC 可运行数）+ integration/demo/c_demo/link_test
6. test_package：test_package.cpp（版本宏+对象 API）+ test_ohos.cpp（真实栈展开）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 配置阶段 autoconfig 选择 dbghelp 符号化后端，编译报 `windows.h not found` | CMake 无 HarmonyOS 平台模块，`CMAKE_SYSTEM_NAME=HarmonyOS` 时 `UNIX` 变量未定义，autoconfig 走到 else 分支（Windows） | CMakeToolchain 强制 `CMAKE_SYSTEM_NAME=Linux`（HarmonyOS 内核基于 Linux，平台语义等价，同 E092/E140 方案） |
| 2 | 栈追踪输出 0 帧（空栈） | OHOS musl 下 clang 默认优化不发射 unwind tables，`_Unwind_Backtrace` 无 .eh_frame 可走 | 库编译（CPPTRACE 场景由上游 CMake 对库自身处理）与测试/消费方编译加 `-funwind-tables`；test_package 的 CMakeLists 对两个测试目标显式添加 |
| 3 | `libdwarf.h file not found`（find_package 成功但 include 不传导） | conan CMakeDeps 生成的 target 属性带 `$<$<CONFIG:Release>:...>` generator expression，构建类型非 Release（RelWithDebInfo）时不匹配 | 构建类型与 conan profile 的 `build_type=Release` 严格对齐（conan create 自动一致） |
| 4 | FetchContent 下载 zstd/libdwarf/googletest 卡住 | CI 网络无法访问 GitHub | 上游原生开关 `CPPTRACE_USE_EXTERNAL_LIBDWARF/ZSTD/GTEST=ON` 全部外置到 conan 依赖（libdwarf/0.11.1、gtest/1.17.0），无源码补丁 |
| 5 | unittest 的 GTest 链接 target 名是否兼容 conan gtest | — | 上游 test/CMakeLists.txt 直接链接 `GTest::gtest_main GTest::gmock_main`，与 conan gtest 包（cmake_file_name=gtest，GTestConfig.cmake 提供 GTest::* target）完全兼容，无需 patch |

## 源码修改

无。cpptrace 1.0.4 上游原生支持所有必需开关（外置 libdwarf/zstd/gtest、
unwind/symbols/demangle 后端选择），全平台差异在 CMake 配置层解决。

## 依赖版本

- libdwarf/0.11.1（制品仓已发布；传递 zlib/1.3.1 + zstd/1.5.6）
- gtest/1.17.0（test_requires，仅测试期）

注：cpptrace 默认 FetchContent 拉 libdwarf-lite 2.1.0 + zstd 1.5.7，但制品仓
当前只有 libdwarf/0.11.1；已符号级核对 cpptrace 使用的全部 libdwarf C API
（dwarf_init_path_a、dwarf_srclines_b、dwarf_get_ranges_b 等 47 个）在
0.11.1 中齐备（dwarf_ranges 是 cpptrace 内部成员函数名非 C API，不构成缺失），
且实测 155 用例全过含符号化路径验证。

## 上游测试核验（rule4 口径）

- 上游注册口径：`test/unit/` 源码审计——**158 个 `TEST/TEST_F` 声明**（144 `TEST` + 14 `TEST_F`，17 个翻译单元，24 套件）。审核员 Septest 从 tag v1.0.4 实测同口径 158。初版 PR 误将 14 个 `TEST_F`（result.cpp 11 + general.cpp 3）漏算、且把 4 个非 GTest 演示可执行计入 GTest 单元数（144+4=148），净少报 10——已修正为 158。
- 158 → 运行期 155 的差异（3 个用例，上游条件编译排除，非参数化展开）：
  - `FromCurrent.SEHBasic` / `FromCurrent.SEHCorrectHandler`：`#ifdef _MSC_VER`（MSVC SEH 异常处理专用，Linux/macOS/OHOS 全平台一致排除）
  - `Stacktrace.InlineResolution`：`#if defined(CPPTRACE_GET_SYMBOLS_WITH_LIBDWARF) && !defined(CPPTRACE_BUILD_NO_SYMBOLS)`——该宏在根 CMakeLists.txt:340 以 `target_compile_definitions(... PRIVATE ...)` 只对库自身定义，不传播到测试翻译单元，所有非 MSVC 平台（含上游 Linux CI）一致排除
  - 排除后可运行 155 用例：tracing 36（FromCurrent 4/FromCurrentTryCatch 3/TryCatch 15/Rethrow 3/ObjectTrace 4/RawTrace 2/Stacktrace 4/TracedException 1）+ internals 61（OptionalTest 11/LruCacheTest 9/ResultFixture 11/SpanTest 3/SplitTest 7/JoinTest 3/ByteSwapTest 8/RaiiWrapperTest 3/MaybeOwnedTest 2/NDigitsTest 1）+ lib 58（FormatterTest 22/NullableTest 7/PruneSymbolTests 29）
- `add_test` 注册 unittest（gtest），另有 integration/demo/c_demo/link_test 四个测试可执行（上游 CI unittest.py 以 `./unittest` + demo 可执行 exit code 运行）。
- CXX20 module 变体（unittest_module/integration_modules/link_test_modules）需 Clang≥16 + C++20，OHOS clang15/C++17 不实例化（平台限制，豁免申报）。
- 实测结果（HarmonyOS PC arm64 真机）：
  - unittest：155/155 PASSED（100%），含全部 14 个 TEST_F 用例（ResultFixture 11 + RaiiWrapperTest 3，逐项 OK 记录见 _upstream_unittest.log）
  - integration：37 行输出与 expected/linux.txt 文件名+行号 100% 匹配
    （符号因 libc++/libstdc++ ABI 命名差异不同——demangle 输出
    `std::__n1::basic_string` vs `std::__cxx11::basic_string`，结构等价）
  - demo / c_demo / link_test：exit=0
  - c_demo 的 C API 栈追踪输出为空帧：musl 下 C 程序无 C++ 帧信息且 demo
    未开启 rdynamic 导出符号，属展示性 demo（无断言校验），exit=0 通过

## 验证结果

- 平台：HarmonyOS PC arm64；Conan profile：ci/conan/profiles/ohos-aarch64
- conan create：libcpptrace.a 构建安装成功，cmake target `cpptrace::cpptrace`
- 上游测试：unittest 155/155（100%，158 声明中非 MSVC 平台可运行的 155 用例）+ 4 个测试可执行全部通过
- test_package：test_package（版本宏/对象 API/帧渲染）+ test_cpptrace_ohos
  （真实栈展开 ≥2 帧 + libdwarf 符号解析出 文件名:行号）通过
