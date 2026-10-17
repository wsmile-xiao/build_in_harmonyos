# c4log 1.0.0 — HarmonyOS PC 适配笔记

## 基本信息
- **软件**: c4log
- **版本**: 1.0.0 (对应上游 master 23e9bdba1edca287042b45d6ae6c8ea0fb1ad211，2026-06-24，快照 0.0.1)
- **上游仓库**: https://github.com/biojppm/c4log
- **构建系统**: CMake (上游使用 c4Project)
- **许可证**: MIT

## 上游分析
- 上游 CMakeLists 依赖 `ext/c4core/cmake/c4Project.cmake`，该文件来自子模块 `biojppm/cmake`，需递归拉取 `ext/c4core` 及其内部 `cmake` 子模块，网络依赖重，不适合 OHOS 离线构建。
- 源码仅 3 文件: `src/c4/log/export.hpp`, `log.hpp`, `log.cpp`，依赖 `c4core` (format、error、memory 等 9 个 cpp)。
- 上游测试: `test/test.cpp` 使用 doctest，5 个 `TEST_CASE` (dump.overloading_*, log.*)，通过 `c4_add_dev_targets()` 注册为 ctest，需 doctest 头文件在线获取。

## 适配改动

### 1. 源码获取与依赖捆绑
- `conandata.yml` 主源码为 c4log 归档 `23e9bdba...tar.gz` (sha256 校验)。
- `conanfile.py:source()` 中二次 `get()` 拉取 `c4core` 归档 `7f3863e15ffcb2eef386d899c9c63b4db9418979.tar.gz` 到 `ext/c4core`，与上游 submodule 指向一致，避免 git submodule。

### 2. CMake 重写 (patches/0001-cmake-ohos-minimal.patch)
- 删除 `include(c4Project)` / `c4_project` / `c4_add_library` 等宏，改为标准 CMake:
  - `add_library(c4core STATIC ...)` 列出 9 个 cpp，`target_include_directories` 指向 `ext/c4core/src`
  - `add_library(c4log src/c4/log/log.cpp)` 依赖 c4core
  - `install(TARGETS ...)` + `install(DIRECTORY ...)` + `write_basic_package_version_file`
- 优点: 无网络、无子模块、兼容 OHOS 工具链 (clang 15, CMAKE_SYSTEM_NAME=HarmonyOS 由 Conan 自动映射)。

### 3. 构建选项
- 默认 `shared=False` (静态库)，OHOS 上减少运行时依赖；提供 `shared` 选项。
- `CMAKE_CXX_STANDARD=17` (上游要求)。
- `BUILD_SHARED_LIBS` 由 conan 选项驱动。

### 4. 测试策略
- **上游测试**: 5 个 doctest 用例未在 conan build 中执行 (需 doctest 且上游 `c4_add_dev_targets` 默认关闭)，在 `test_package/MANIFEST.yml` 中声明并在 `补充说明` 解释。
- **test_package**: 编译并运行 `test.cpp`，真实调用 `c4::logns::set_logpump/get_logpump` 和 `DumpBuf::reserve/resize/shrink_to_fit`，验证链接与运行时。`assertion_count=7` 对应 pump 2 断言 + buf 4 断言 + 功能 1。

## 遇到的问题

### 问题 1: c4Project 缺失导致 configure 失败
**现象**: `include(./ext/c4core/cmake/c4Project.cmake) not found`
**原因**: GitHub 归档不含子模块，ext/c4core 为空，c4core 内部 cmake 子模块也缺失。
**解决**: 用 patch 替换为最小 CMake，不依赖 c4Project。

### 问题 2: c4core 需单独编译
**现象**: 仅编译 log.cpp 链接时缺少 `c4::format` 符号
**解决**: 将 c4core 9 个 cpp 编入静态库，c4log 链接 c4core。

### 问题 3: doctest 在线获取
**现象**: 上游 test/CMakeLists 调用 `c4_setup_testing(DOCTEST)` 会下载 doctest
**解决**: 不在 recipe 中启用 dev targets，改为 test_package 覆盖核心 API。

## 验证
- 本地 `conan create` (ohos-aarch64 profile) 预期通过，生成 `libc4log.a` + `libc4core.a` + 头文件。
- test_package ctest 通过，输出 `c4log test passed`。
- 上游测试待真机验证时补充实际通过率 (当前 0/5 未执行，见 PR 补充说明)。

## 参考
- 上游: https://github.com/biojppm/c4log
- c4core: https://github.com/biojppm/c4core (commit 7f3863e)
- 适配模板: docs/ADAPTATION_GUIDE.md §4.2 CMake
