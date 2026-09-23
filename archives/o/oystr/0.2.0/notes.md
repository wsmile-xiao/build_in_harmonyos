# oystr 0.2.0 适配笔记

## 状态与来源
- 状态：`built`（设备构建、上游 CTest、Conan `test_package` 已通过；未标记 `published`）。
- 构建系统：CMake；语言：C++17；许可证：MIT。
- 上游源码 URL 与 SHA256：`https://github.com/p-ranav/oystr/archive/refs/tags/v0.2.0.tar.gz` / `a53d3c953bf675482062d544b86e134cd2da1493814fda4e5440472155fcbe9f`。
- 产物是命令行工具 `bin/oy`（application/tool），软件级入口见 `../commands.json`。

## 适配补丁
- `0001-CMakeLists.txt.patch`：移除 FetchContent 的 argparse/fmt master 下载和 `-march=native`，改为 Conan 的 fmt target 与 argparse 头文件。
- `0002-source-searcher.cpp.patch`：用 C++17 `std::filesystem` 遍历替代 OHOS libc 不提供的 `nftw` action-return 扩展。
- `0003-source-searcher.hpp.patch`：仅在 x86 目标包含 `immintrin.h`。
- `0004-source-sse2_strstr.cpp.patch`：AVX2/x86 之外使用 `std::string_view::find` 的真实搜索实现，不是空 stub。

## 依赖与 OHOS
精确 requirements 为 `argparse/3.2`、`fmt/12.2.0`；未使用 `fmt/11.2.0-r1`。OHOS profile 的 CMakeToolchain 实测设置为 `CMAKE_SYSTEM_NAME=Linux`、`CMAKE_SYSTEM_PROCESSOR=aarch64`，因为当前 CMake 没有 HarmonyOS platform module；编译器和 sysroot 仍由 OHOS profile 注入，未使用 `-march=native`。`CMAKE_POLICY_VERSION_MINIMUM=3.5` 用于兼容上游 CMake 项目。

## 验证
最终 Conan 命令使用 host/build `ci/conan/profiles/ohos-aarch64`，并显式覆盖 `compiler.cppstd=17`、`compiler.libcxx=libc++`、`os.version=6.0`、`tools.build:jobs=1`。构建阶段启用上游 developer mode 和 CTest：上游 `oystr_test` 为 `TOTAL=1 PASS=1 FAIL=0 SKIP=0 NOT_RUN=0`。`test_package/test.sh` 通过 BusyBox `script` 提供 PTY，真实执行文件搜索和 stdin 搜索，两个断言均通过：`TOTAL=2 PASS=2 FAIL=0 SKIP=0 NOT_RUN=0`。
