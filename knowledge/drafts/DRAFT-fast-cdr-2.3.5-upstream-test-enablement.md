# DRAFT-fast-cdr-2.3.5-upstream-test-enablement — 启用被顶层 FORCE OFF 的上游 GTest 测试套件

**路径**: B（知识库扩展）
**来源任务**: fast-cdr-2.3.5-r02-upstream-test-gate-recovery-pc1-11-20260903T025121Z
**触发事件**: R02 返工启用快速 Fast-CDR v2.3.5 上游测试门禁（R01 以 BUILD_TESTING=OFF 未达标）

## 问题

Fast-CDR 2.3.5 的 `test/CMakeLists.txt` 在 `BUILD_TESTING=ON` 时编译上游 GTest 套件（`test/cdr`、`test/xcdr` 及 `cmake.force_standard` 模块测试）。但顶层 `CMakeLists.txt` 在 `project()` 之前执行：

```cmake
if(NOT BUILD_TESTING)
    message(STATUS "Tests not compiled by default")
    set(BUILD_TESTING OFF CACHE BOOL "Enable testing" FORCE)
endif()
```

Conan 配方 `CMakeToolchain` 的 `tc.variables["BUILD_TESTING"]="ON"` 写入生成的 `conan_toolchain.cmake`（`set(... CACHE STRING)`），而 toolchain 文件在 `project()` 阶段才加载，晚于顶层 if 求值——顶层已 FORCE 出 OFF，toolchain 的非 FORCE set 不覆盖，测试永不编译（conan-verify 日志可见 `Tests not compiled by default`）。

即使 `BUILD_TESTING=ON` 生效，上游 `find_or_add_gtest()`（非 ROS 分支）执行 `find_package(GTest CONFIG REQUIRED)` 并链接 `GTest::gtest_main`；ohpcd 的 `gtest/1.17.0` 配方 `package_info` 只声明单个 `gtest::gtest` target，CMakeDeps 生成的 `gtest-config.cmake` 不含 `GTest::gtest_main` → 链接期 `target was not found`。

## 根因

1. 顶层 `if(NOT BUILD_TESTING)` 在 `project()`（toolchain 加载点）之前求值，未定义时 FORCE 写入 OFF 缓存；
2. conan `tc.variables` 生成的 toolchain `set(BUILD_TESTING ... CACHE)` 在 project() 后执行，缓存已有值且非 FORCE → 不覆盖。必须经 cmake 命令行 `-D` 传入才能在顶层 if 前生效；
3. gtest 配方 `package_info` 只声明 `gtest::gtest`，CMakeDeps 生成物不含 `GTest::gtest_main`。

## 方案

1. `build()` 中用 `cmake.configure(variables={"BUILD_TESTING": "ON"})`，让 `-DBUILD_TESTING=ON` 进命令行，顶层 if 前即可见 ON；
2. `generate()` 中把 `GTest_DIR` 指向 gtest 包内官方 `lib/cmake/GTest/GTestConfig.cmake`（googletest 上游安装产物，含 `GTest::gtest/gtest_main/gmock/gmock_main` 完整 IMPORTED targets，指向包内 `libgtest*.a`）：

```python
gtest_pkg = self.dependencies["gtest"].package_folder
tc.variables["GTest_DIR"] = os.path.join(gtest_pkg, "lib", "cmake", "GTest")
```

3. 勿给 CMakeLists.txt 打补丁改顶层 if（FORCE 是上游语义），勿用 `--no-preflight` 绕过。

## 验证

- R02 修复后 `ohc-run.py conan-verify fast-cdr 2.3.5` G2 通过
- 上游 4 个 GTest 可执行入口（UnitTests / FixedSizeStringTests / ArrayAsSTDVectorTests / xcdr_tests）+ 4 个 ctest 模块测试全部构建运行
- `ctest --output-on-failure -j4` 全量：`100% tests passed, 0 tests failed out of 2107`（20.02s，exit 0）
- 日志 `/storage/Users/currentUser/tmp/fast-cdr-r02-upstream-ctest.log`，SHA-256 `1a1f8dbeb60c114bed274563aa13cc783fcb286335329e8c415aa6a6f2e1375a`

## 适用边界

- OHOS 上任何"链接 `GTest::gtest_main` / 构建上游 GTest 套件"的 CMake 库可复用同一模式：BUILD_TESTING 经 `-D` 注入 + `GTest_DIR` 指向包内官方 config
- 依赖 gtest 包内包含官方 GTestConfig.cmake（googletest 安装产物）；若某发布版未安装，需改走 `replace_in_file` 把 `GTest::gtest_main` 替换为实际 target，或要求 gtest 配方补组件
- `BUILD_TESTING` 顶层 FORCE 模式为 Fast-CDR 特有；其它项目若无顶层 if 则不适用 `-D` 注入要求

## 反例与限制

- 禁止修改上游 CMakeLists 顶层 if（上游语义，会产生源码补丁且影响 CI 一致性）
- 禁止把 `gtest` 从 requirements 移除或用 `--build=missing` 绕过依赖解析
- 库本体产物（libfastcdr.a、安装内容、package_info）不受测试开关影响；新增 gtest 仅为 build 依赖

## 查重差异

- E092（CMAKE_SYSTEM_NAME=Linux）：平台映射，不同主题
- E022/E023（sem_unlink/locale 测试失败）：测试运行时兼容问题，非测试未构建
- E451（ccls ClangIndex target not found）：find_package(Clang) target 缺失，库/根因不同
- E473（SDL2_image WebP::webpdemux target not found）：libwebp 配方组件缺失，与 libgtest 场景相近但根因/方案不同（E473 靠配方组件/Find 模块，本条目靠包内官方 GTestConfig.cmake）
- 本条目不与以上任何一条等价，且对 OHOS CMake+GTest 上游测试启用具有跨库复用价值