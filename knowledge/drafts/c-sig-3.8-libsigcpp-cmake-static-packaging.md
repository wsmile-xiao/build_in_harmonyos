# c-sig 3.8（libsigc++ 3.8.0）上游 CMake 静态打包适配范式

> Draft: DRAFT-CSIG-LIBSIGCPP-380-CMAKE-STATIC-PACKAGING
> Stem: `c-sig-3.8-libsigcpp-cmake-static-packaging` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-CSIG-LIBSIGCPP-380-CMAKE-STATIC-PACKAGING
- **严重度**: 2
- **类别**: conan-recipe-cmake-packaging
- **触发工具**: conan|cmake|make
- **阶段**: installation|packaging|testing

## 错误特征

```
add_library(${SIGCPP_LIB_NAME} SHARED ${SOURCE_FILES})   # 上游写死 SHARED
install (TARGETS ... LIBRARY DESTINATION "lib" ...)       # 只有 LIBRARY 目标位置
set( CMAKE_CXX_STANDARD 17 )                              # 覆盖 profile cppstd
```

症状：Conan `shared=False`（R26 静态默认）构建时要么不产出静态归档，要么
`cmake.install()` 后 `lib/` 里没有 `.a`（L5 失败）；或 profile 的
`compiler.cppstd` 不生效。

## 根因分析

libsigc++ 3.8.0 的 CMake 构建从未为包管理器设计：

1. `sigc++/CMakeLists.txt` 把库类型写死为 `SHARED`，`BUILD_SHARED_LIBS`
   完全不起作用；
2. `install(TARGETS ...)` 只声明 `LIBRARY DESTINATION`，静态归档
   （ARCHIVE）与可执行产物（RUNTIME）没有安装位置；
3. 根 `CMakeLists.txt` 硬编码 `CMAKE_CXX_STANDARD 17`，覆盖 Conan profile。

另外 **3.8.0 tarball 同时带 Autotools（configure.ac）、Meson（meson.build）、
CMake（CMakeLists.txt）三套构建**；仓库旧版 libsigc/3.0.6 用的是 Meson 配方，
照抄会走错路（Meson 在 3.8 不是首选，conan-center libsigcpp/3.x.x 已切 CMake）。

## 解决方案

**主方案**: three-single-purpose-patches-keep-tests

补丁链按单一职责拆分（全部 `patch -p1 --fuzz=0` 干净应用）：

| # | 改动 | 目的 |
|---|------|------|
| 0001 | `add_library(${NAME} ${SOURCE_FILES})`（去 SHARED）+ install 增加 `ARCHIVE DESTINATION "lib"`、`RUNTIME DESTINATION "bin"` | 让 `BUILD_SHARED_LIBS` 真正控制产物并落盘 |
| 0002 | 删 `set(CMAKE_CXX_STANDARD 17)` | profile `compiler.cppstd` 生效 |
| 0003 | 只删 `add_subdirectory(examples)`，**保留 `add_subdirectory(tests)`** | 省构建时间且 L1 有上游测试证据 |

**与 conan-center 的关键差异**：CCI 的 3.8.0 补丁把 examples 和 tests 一起删了
（CCI 不跑上游测试）；本仓库规范要求上游测试进 `build()`，因此保留 tests，
`cmake.test()`（ctest）运行全部 42 个用例。

打包细节：

- 产物保留上游命名：`libsigc-3.0` / `include/sigc++-3.0`；生成的
  `sigc++config.h` 在 `lib/sigc++-3.0/include/`，`package_info().includedirs`
  必须同时声明两个 include 目录。
- `package()` 里 `rmdir lib/cmake`、`lib/pkgconfig`，避免上游生成的
  Config 文件与 CMakeDeps/PkgConfigDeps 属性冲突。

**消费者测试适配点**：libsigc++ 3.x `connection::disconnect()` 返回 **void**
（2.x 返回 bool），断言要用 `!conn.connected()`，不能吃返回值（真机 clang 15
报 `invalid argument type 'void' to unary expression`）。

## 验证

```sh
conan create archives/c/c-sig/3.8 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing -nr
# 真机（10.62.134.118）实测：exit 0；ctest 42/42 Passed（3.36s）；
# test_package 两用例 PASS（19 + 16 断言）；libsigc-3.0.a 62,732B
```

## 关联条目

- E288（CMake 双库目标收敛）、E360（static-only 构建保持导出身份）：同为
  CMake 打包类，但均不覆盖"上游硬编码 SHARED + install 缺目标位置"的补丁范式；
- E294（共享包第二静态构建树恢复上游测试）：同样主张保留上游测试，视角不同。
