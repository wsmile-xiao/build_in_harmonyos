# DRAFT-E998-draft-E047：无构建系统纯 C 库注入 CMakeLists.txt（error-detection 2.1.1）

> Contributor: pc4-50 (agent E047) | Status: Draft | Updated: 2026-09-26
> Source: error-detection 2.1.1 适配（feat/error-detection-2.1.1）
> 对应：`knowledge/drafts/E998-draft-E047.kv`

## 现象

上游 error-detection 官方源码仅含 `Sources/err.c` + `Sources/err.h` 两个文件
（+ 文档），**无 configure、无 Makefile、无 CMakeLists.txt**。init-build 按
autotools 模板生成的配方无法直接构建；直接手写 clang 编译还须处理
basic_layout 的 source_folder 路径，且 Conan 2.29 无 `tools.build:archiver`
conf（归档器只能写死 llvm-ar）。

## 方案（source() 注入 CMakeLists.txt + 标准 CMake 流程）

conanfile.py 在 `source()` 阶段用 `save()` 注入最小 CMakeLists.txt：

```cmake
add_library(error-detection Sources/err.c)
target_include_directories(error-detection PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/Sources>
    $<INSTALL_INTERFACE:include>)
set_target_properties(error-detection PROPERTIES
    PUBLIC_HEADER "Sources/err.h" C_STANDARD 99 POSITION_INDEPENDENT_CODE ON)
install(TARGETS error-detection EXPORT error-detectionTargets ...)
install(EXPORT error-detectionTargets ... NAMESPACE error-detection::)
```

`generate()` 用 `CMakeToolchain`，`build()` 走 `cmake.configure()/build()`，
`package()` 用 `cmake.install()`，`package_info()` 填 `cpp_info.libs` +
`cmake_target_name = error-detection::error-detection`。库编译期 C 标准设为
C99（err.c 用 `for` 内声明与复合字面量无关，但 C99 更稳妥）。

## 与既有知识的差异（查重）

- `DRAFT-cobs-c-0.4-no-build-system-pure-c-conan-recipe` 提供**手写
  clang/llvm-ar 直接编译**方案（`custom-build-direct-compile-with-source-folder`）；
  本条目提供**注入 CMakeLists + 标准 CMakeToolchain**方案。两者触发面相同
  （无构建系统纯 C 库），但方案不同：CMake 注入免去 basic_layout 路径坑与
  archiver conf 问题，产物可复用 CMake 安装/导出体系。
  `similar_to: [DRAFT-cobs-c-0.4-...]`，属部分覆盖 + 新增差异，非完整重复。

## 验证

- `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing` 通过，
  test_package 6 项断言（checkSum8/16/32 + CRC-8/16/32 标准校验向量）全过。

## 适用边界

- 适用：源文件数量少（1~10 个）、无任何构建系统的纯 C 库。
- 反例：库有 autotools/CMake 原生构建系统时应直接复用；头文件库走 header-only
  配方；含复杂生成步骤的库不宜强行注入 CMakeLists。
