# apngasm 3.1.10 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

使用 Conan 2 驱动构建，CMake 构建系统：
1. conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
2. CMake 自动配置、编译 lib (shared+static) 和 cli (apngasm executable)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | zlib 版本冲突 | boost/1.84.0 requires zlib/1.3.1, libpng/1.6.58 requires zlib/1.3.1.1 | 使用 libpng/1.6.39 (依赖 zlib/1.3.1) 与 boost 版本一致 |
| 2 | CLI 编译找不到 png.h | cli/CMakeLists.txt 未调用 find_package(PNG/ZLIB) | 补丁添加 find_package 和 include_directories |
| 3 | CLI 链接时找不到 libapngasm | 并行构建时 CLI 先于库链接 | 补丁添加 add_dependencies(apngasm-cli apngasm-dynamic apngasm-static) |
| 4 | test_package 找不到 png.h | libpng recipe 未设置 cpp_info.includedirs | test_package CMakeLists.txt 显式添加 include 路径 |
| 5 | CI L0 stub_test_method | test() 用 cmake.test() 而非 self.run() | 改用 self.run(test_bin) 直接执行测试二进制 |

## 源码修改

- patches/0001-cli-add-png-zlib-includes.patch: CLI CMakeLists.txt 添加 PNG/ZLIB find_package 和 include_directories，添加 add_dependencies 确保构建顺序

## 依赖版本

- libpng/1.6.39
- boost/1.84.0
- zlib/1.3.1

## 验证结果

conan create 成功构建，test_package 通过 (apngasm version 输出验证)

---

**编译结束**: 2026-08-27
**最终状态**: built
