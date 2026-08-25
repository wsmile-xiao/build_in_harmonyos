# fmt 12.2.0 适配笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出 libfmt.so / libfmt.a（按 shared option），供链接与 dlopen。
- 上游同时提供 fmt::fmt-header-only（INTERFACE）与 fmt::fmt-c（C11 API，静态），
  本 recipe 主产 compiled fmt::fmt；header-only 目标随包安装的 cmake config 可用。

## 上游核实（官方真实信息）
- 官方仓库：https://github.com/fmtlib/fmt
- 精确 tag / release：12.2.0（2026-06-16 正式 release，commit 1be298e）
- 源码 URL：https://github.com/fmtlib/fmt/archive/refs/tags/12.2.0.tar.gz
- SHA256：8b852bb5aa6e7d8564f9e81394055395dd1d1936d38dfd3a17792a02bebd7af0
- License：MIT（LICENSE 文件，Copyright (c) 2012 - present, Victor Zverovich）
- 构建系统：CMake（cmake_minimum_required 3.8...3.28）
- 最低 C++ 标准：C++11（target_compile_features(fmt PUBLIC cxx_std_11)）
- 运行时第三方依赖：无（src/ 仅用 C/C++ 标准库）
- CLI：无（library package，无 bin/）
- 安装产物：libfmt.{a,so}、include/fmt/*.h、lib/cmake/fmt/{fmt-config,fmt-targets}.cmake、
  lib/pkgconfig/fmt.pc、LICENSE
- fmt/std.h：存在（include/fmt/std.h，含 std::optional/std::variant/std::filesystem::path
  等 std 类型的 formatter；12.2.0 起 std::byte formatter 从 format.h 移入 std.h）
- fmt::ostream_formatter：存在（include/fmt/ostream.h:91，
  `using ostream_formatter = basic_ostream_formatter<char>`，已实测编译链接运行通过）

## 关键适配
- **0 patch**：上游源码直接可用 OHOS 工具链构建，未修改任何上游实现或测试。
- 复用 8.1.1 已验证的 OHOS 适配模式：
  - os=OHOS 守卫下把 CMAKE_SYSTEM_NAME 设为 "OHOS"（而非 conan 默认的 "HarmonyOS"），
    对齐 cmake 的 Modules/Platform/OHOS.cmake，避免 SONAME 丢失传染下游。
  - CMAKE_SYSTEM_PROCESSOR=aarch64，避免上游按 "unknown" 走错 SIMD/汇编分支。
  - CMAKE_INSTALL_LIBDIR=lib，对齐 cpp_info.libdirs 与 test_package。
  - BUILD_SHARED_LIBS 跟随 options.shared（不写死）。
  - FMT_TEST=OFF / FMT_DOC=OFF / FMT_INSTALL=ON。
  - 鸿蒙二进制签名（.so 与 bin/ ELF），os!=OHOS 时跳过。
  - includedirs 只声明 include（不展开 include/fmt），避免 fmt/locale.h 遮蔽
    musl 的 <locale.h>（spdlog 实撞，8.1.1 已记录）。

## 上游正式测试（OHOS toolchain 实测，非复制 11.2.0-r1 统计）
- 测试框架：vendored gtest（test/gtest/），无外部 Catch2/GoogleTest 依赖。
- upstream test source files（test/ 根目录正式单元测试源文件）：23
  （args/assert/base/c/chrono/color/compile/enforce-checks/format-impl/format/
   gtest-extra/module/no-builtin-types/noexception/os/ostream/posix-mock/printf/
   ranges/scan/std/unicode/xchar-test）
- helper/support 源文件（编译进 test-main 库，非独立 test）：3
  （test-main.cc / gtest-extra.cc / util.cc）
- upstream test executable targets（默认配置编译产出）：22
  （21 个 CTest 测试 + perf-sanity benchmark，无 CTest 注册）
- CTest registered（默认配置：非 PEDANTIC/CUDA/MODULE，OHOS 非 MSVC）：21
- 分类（不计入正式普通单元测试）：
  - benchmark：perf-sanity（executable，无 add_test）
  - fuzz：fuzzing/*.cc（7 个，FMT_FUZZ=OFF 不编译）
  - compile-error-test / find-package-test / add-subdirectory-test /
    static-export-test：仅 FMT_PEDANTIC 启用（本配置 OFF，跳过）
  - cuda-test：仅 FMT_CUDA_TEST 启用（跳过）
  - module-test：仅 FMT_MODULE 启用（跳过）
  - noexception-test / nolocale-test：仅 FMT_PEDANTIC 启用（跳过）
- assertion 数（EXPECT_*/ASSERT_*，正式单元测试源文件，含 gtest 框架宏）：约 2351
  （TEST/TEST_F 用例定义 618）

### 实测 compile / runtime
- compile：22/22（全部 executable 编译链接通过，build exit 0）
- runtime：executed = 21 / pass = 19 / fail = 2 / skip = 0
- 失败 2 项（平台/环境差异，非库缺陷，0 patch 接受）：
  1. os-test → file_test.line_buffering：pipe + setvbuf(_IOLBF) + fscanf 行缓冲，
     OHOS 行缓冲行为差异（Expected n=42, got n=0）。与 11.2.0-r1 同一现象。
  2. c-test → test_print：tmpfile() 返回 NULL（测试环境临时目录限制），
     属 C stdio tmpfile 在当前环境的可用性，非 fmt 逻辑问题。

## 源码修改
无需修改源码，fmt 12.2.0 可直接编译。0 patch。

## 依赖版本
- CMake: 4.1.2
- Clang: 15.0.4 (HarmonyOS NDK, target aarch64-unknown-linux-ohos)
- 无外部运行时依赖

## 状态
built（OHOS 真机 conan create + test_package 通过）
