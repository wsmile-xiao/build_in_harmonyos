# DRAFT-ini-cpp-2.0.0-header-only-gtest-submodule-missing-direct-compile

> 状态: Draft | 库: ini-cpp 2.0.0 | 日期: 2026-09-22
> 来源: ini-cpp 2.0.0 适配（PC2 executor, task ini-cpp-2.0.0-r01）

## 问题（现象）

header-only C++ 库的 release tarball 不含 googletest git submodule（空目录），
上游测试 `test/tests.cpp`（27 个 GTest TEST 用例）无法通过上游 CMake 构建：
顶层 CMakeLists 仅在 Debug 模式 `ADD_SUBDIRECTORY(googletest)` +
`ADD_SUBDIRECTORY(test)`，而 `googletest/` 为空目录；直接配置会因
`Cannot find source file` 或找不到 gtest 头失败。

## 根因

- GitHub `/archive/refs/tags/<tag>.tar.gz` 是 git archive 产物，submodule 内容
  不导出（只留下空目录）。
- 上游测试依赖 googletest submodule 编译，tarball 无 submodule → 测试框架缺失。
- 若 test/CMakeLists.txt 用 `INCLUDE_DIRECTORIES(${PROJECT_SOURCE_DIR}/googletest/googletest/include)`
  硬编码路径，则无法直接指向 Conan 包的头目录。

## 方案（rec_approach）

header-only 库无需编译库本体，在 `build()` 内直接跑上游测试：

1. `test_requires("gtest/1.17.0")`（ohpcd 已发布，配 revision ab1bc3bf…）——
   不进入消费者依赖图，只供本包 build() 使用（DRAFT-332 同口径：test_requires
   是 GTest 接法正解，tool_requires+build_context 会渲染不全）。
2. 不依赖上游 CMake 测试目标，用 profile 编译器直接编译测试源：
   `clang++ -std=c++17 -I<src> -I<gtest include> test/tests.cpp -o all_test -L<gtest lib> -lgtest -lgtest_main`
   - 编译器必须取 `tools.build:compiler_executables` conf（OHOS 沙箱 subprocess
     不搜 PATH，posix_spawn 差异——与 inipp/rich/vc 同源教训）。
   - 链接 gtest 包内静态库（libgtest.a / libgtest_main.a）。
3. **fixtures 手工复制到运行目录**：上游 test/CMakeLists.txt 由 CMake
   `file(COPY test/fixtures DESTINATION <build>)` 自动复制；直接编译时测试
   二进制按相对路径 `./fixtures/config.ini` 读取，必须手动把 `test/fixtures/`
   复制到 `cwd` 下（`cwd=build_folder`）。
4. 运行 all_test，回填真实通过率（rule 4/R51）。

## 验证

- ini-cpp 2.0.0 实测：27/27 PASSED（INIReader 24 + INIWriter 3，46ms）。
- test_package（sample.cpp：Sections/Keys/Get<T> 类型访问）ctest 1/1 通过。

## 适用边界

- 适用于 header-only（或无需链接产物）库且上游测试为 GTest 单文件/少文件场景。
- 上游测试为多目录、依赖复杂资产（如 openrct2 replays/objects zip）时不可直接
  套用，走 DRAFT-332 的测试资产三件套路线。
- 上游测试需要 CMake 生成配置/多目标时，仍应走 CMake + GTest_DIR 官方 config
  路线（fast-cdr 模式）。

## 反例与限制

- 不能把 release tarball 缺 submodule 当作"上游无测试"上报（rule4 拒绝）。
- 直接编译要求测试源自包含（仅依赖 gtest + 被测头），不适用需要 CMake 宏/
  生成源码的测试。

## 查重差异

- DRAFT-332-openrct2：GTest 接法同源（test_requires 正解），但聚焦复杂测试
  资产（replays/objects zip）与 ctest 逐用例，未覆盖"直接编译 + fixtures
  手工复制"这一轻量路径。
- DRAFT-ctre-3.10.0-header-only-recipe-test-package：header-only 配方通用要点
  （libc++/codeload filename/CTest 注册），未覆盖 submodule 缺失时测试框架
  替代接法。
- E332/E342：网络下载 googletest 的分离/禁用，场景不同（本条目无网络下载）。
- E425/E426：pico-sdk submodule 空目录保持，功能范围限定，场景不同。
