# libint 1.2.1 适配笔记

## 编译环境
- 构建系统: cmake（上游 Psi4 移植路径，README_CMake.md 推荐；ExternalProject 链）
- 编译日期: 2026-09-25
- 编译器: clang/clang++ 15（OHOS SDK，`/data/service/hnp/bin/clang`）
- 目标平台: OpenHarmony / HarmonyOS PC，aarch64（原生构建，非交叉）
- Conan: 2.x（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- 状态: built

## 编译步骤

1. **源码**：官方 GitHub tag `release-1-2-1` 归档
   `https://github.com/evaleev/libint/archive/refs/tags/release-1-2-1.tar.gz`
   （sha256 `fe5900c98d6adfeadb69cecee9895548ef69b5464f9c2cfb85bd315cf349f3a4`）。
   该 tag 与 Debian/Ubuntu 发行的 `libint_1.2.1.orig.tar.gz` 逐字节一致
   （顶层目录 `libint-release-1-2-1/`，同一 sha256），即官方 Libint1 1.2.1 发布源。

   > 注意：**Libint1**（1.x）与 libint2 是同作者的*不同*代码库。libint1 的
   > release tag 是**源码树**，不从 GitHub Release 发 pre-generated 资产，
   > 只发到 sourceforge v1-releases（那里最新到 1.1.5）。libint-1.2.1 的
   > release tag 不含预生成积分核，需构建期由 `libint_compiler` 生成。

2. **依赖**：**无**。libint1 是纯 C/C++ 的积分库，运行期不需要 GMP/MPFR/Boost
   /Eigen（这些只是 libint2 / libint 编译器高级路径的可选依赖）。本 CMake 路径
   也不需要 perl/autotools。

3. **构建**（`conan create`）：
   ```bash
   conan create archives/l/libint/1.2.1 \
     -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
     --build="libint/*"
   ```
   `generate()` 固化：`MAX_AM_ERI=4`（LIBINT_MAX_AM=5，覆盖到 d 壳层）、
   `ENABLE_XHOST=OFF`（去 `-march=native`）、`BUILD_SHARED_LIBS=OFF`（静态）、
   `BUILD_FPIC=ON`，并把 `CMAKE_INSTALL_PREFIX` 指到自包含 staging 前缀
   `${build_folder}/_install`。

4. **打包**：`package()` 里 `cmake --install .`（无 --prefix，用缓存 prefix）
   把 `include/ + lib/ + share/cmake/Libint/` 装进 `_install`，再整目录拷入
   `package_folder`。

5. **上游测试**：libint 1.2.1 **无任何自动化测试**（已审计，见
   `test_package/MANIFEST.yml` 的 `upstream_test_audit`），按 no_tests 口径在
   test_package 里输出 `HMBS_UPSTREAM_TEST_RESULT status=no_tests`。

6. **消费者入口**：`test_package` 提供 1 个入口（C 消费者，10 条断言，ctest 注册
   1 个用例），`conan create` 的 test 阶段经 ctest 真实执行。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 CMake `install(DIRECTORY ${STAGED_INSTALL_PREFIX}/... DESTINATION ${CMAKE_INSTALL_PREFIX})` 把目标前缀在 configure 期固化成绝对路径，conan 的 `cmake.install()` 默认 `--prefix <package_folder>` 无法覆盖这类绝对 DESTINATION | `src/CMakeLists.txt` 用 ExternalProject 先把子项目装到 `${build}/stage${prefix}`，顶层再把 stage 里 `lib/include/share` 拷到 `${CMAKE_INSTALL_PREFIX}`；若 CMAKE_INSTALL_PREFIX 不显式设置就落到 `/usr/local` 污染系统 | `generate()` 显式 `tc.variables["CMAKE_INSTALL_PREFIX"] = ${build_folder}/_install`；`package()` 里 `cmake --install .`（无 --prefix，用缓存 prefix）把一切装进 `_install`，再 `copy(_install → package_folder)`，得到完整自包含布局 |
| 2 | `ENABLE_XHOST` 默认 ON 会往编译器加 `-march=native` | 平台相关优化，破坏可复现性，且属未知 host 探测 | `generate()` 设 `ENABLE_XHOST=OFF` |
| 3 | 首次消费者测试误判 `init_libint(0,1)` 返回 43 为失败 | `init_libint` 成功时返回**正整数 = 分配内存**（非 0），只有 `max_am >= LIBINT_MAX_AM` 才返回 -1 | 按真实契约断言：合法 `max_am=3` → `mem>=0` 且分配栈；非法 `max_am = LIBINT_MAX_AM` → 负值 |
| 4 | 用 autotools 路径的思路（configure.ac + objectdir.pl） | autotools 路径需要 perl 和 autoreconf/autoconf，且在 OHOS 上更不稳；CMake 生成器 `build_libint.c` 是纯 C，无需 perl | 全程选用上游 CMake 路径（Psi4 移植，README_CMake.md 推荐），无 perl/autotools 依赖 |
| 5 | 上游 CMake `project(Libint VERSION 1.2.0)` 与 tag 版本 1.2.1 不一致 | 上游源码自带 quirk（该 Psi4 移植 CMake 基线声明 1.2.0），但不影响 Conan 包版本 | 不处理：Conan 包 version=1.2.1；conan CMakeDeps 生成的 `LibintConfig.cmake` 用 1.2.1，消费者 `find_package(Libint)` 用 C++/C API 不判版本 |
| 6 | 真机预检 configure 阶段报 `CMake Error at CMakeLists.txt:11: Compatibility with CMake < 3.5 has been removed` 中断 | 真机 CMake 4.1.2 已移除对 CMake<3.5 的兼容；上游 5 处 `cmake_minimum_required(VERSION 3.0)` 触硬门槛 | 新增 `patches/0001-*` 把 5 处 `VERSION 3.0` 提升到 `3.5`（恰好跨过 4.x 硬门槛且保留旧项目 OLD 策略兼容），conandata.yml 登记、conanfile source() 里 `apply_conandata_patches` |

## 源码修改

1 个补丁（`patches/0001-bump-cmake-min-version-for-cmake4.patch`）：
- **CMake 4.x 兼容**：把 5 处 `cmake_minimum_required(VERSION 3.0)` 提升到
  `VERSION 3.5`（顶层 `CMakeLists.txt` 与 `src/bin/{libint,libderiv}`、
  `src/lib/{libint,libderiv}` 四个子项目）。真机 CMake 4.1.2 已移除对
  CMake<3.5 的兼容（`Compatibility with CMake < 3.5 has been removed` 直接
  报错中断 configure），升到 3.5 恰好跨过硬门槛，同时保留旧项目最兼容的策略
  行为（3.5~4.x 的策略默认回退 OLD 兼容，不改变旧语义）。
- 其余适配仍在配方层完成（CMake 变量、staging 前缀、`package_info`）。

## 依赖版本

无外部 Conan 依赖。运行期仅链接 libc（libint.a 的 `extern "C"` 入口纯 C 链接，
无需 `-static-libstdc++` / `-lm`）。

## 消费者入口矩阵（test_package）

| # | 入口 | 覆盖面 | 断言数 | 结果 |
|---|------|--------|--------|------|
| 1 | `test_libint`（C） | C API：`libint_storage_required` 内存查询、`init_libint_base` 填充 `build_eri` kernel 分发表（00\|p0 / pp\|pp / ff\|ff 非空）、`init_libint`/`free_libint` 完整生命周期（分配/释放 `int_stack`/`PrimQuartet`）、非法 `max_am>=LIBINT_MAX_AM` 反向证伪 | 10 | 全过 |

入口由 ctest 注册为 1 个用例（`libint_consumer`），`ctest -N` 取 discovered=1、
`Test #N ... Passed` 与 LastTest.log 取 passed=1。

## 验证结果

- 真机预检前本地已用 gcc/clang-cmake 对 release-1-2-1 源码跑通 CMake 全链
  （compiler + 生成的 libint/libderiv 静态库 + 安装布局）并交叉核对
  `find_package(Libint)` + `Libint::int` 消费者编译运行（10 断言全过）。
- 上游测试：无（no_tests，审计见 MANIFEST.yml）。

## 注意事项

- `MAX_AM_ERI` 决定库规模与构建时间（约与 AM^4 成正比）：默认 4（LIBINT_MAX_AM=5）
  覆盖常规 SCF 计算；需要更高角动量用 `-o libint/*:max_am_eri=N` 调整（不同值
  产生不同 Conan 包 ID）。
- `build_eri` 分发表只填了 (is|is) 起的分块（索引 1,2,3…），`[0][0][0][0]`
  (ss|ss) 为 NULL——这是上游设计，不是缺陷；测试抽查真实非空内核。
- `libderiv.a`（导数积分）随包安装到 `lib/`，但默认 `Libint::int` 目标只暴露
  `libint.a`；需要导数的消费者可自行链接 `libderiv.a`。
- 上游 CMake 用的是 `ExternalProject`，嵌套子项目继承顶层
  `${CMAKE_C_COMPILER}/${CMAKE_CXX_COMPILER}` 与 `CMAKE_C_FLAGS/CXX_FLAGS`，
  无独立工具链文件；OHOS 是原生 aarch64 构建，编译器在
  `tools.build:compiler_executables`（profile）提供绝对路径，可正常继承。
