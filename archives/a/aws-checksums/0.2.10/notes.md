# aws-checksums 0.2.10 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-09
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤
标准 CMake 构建，依赖 aws-c-common/0.14.3。

关键点：
1. CMakeLists.txt 调用 `find_package(aws-c-common REQUIRED)`，需要 CMakeDeps 生成配置
2. CMakeLists.txt 引用 AWS CMake 模块 (AwsSIMD, AwsCFlags 等)，需要将 aws-c-common 的 modules 目录加入 CMAKE_MODULE_PATH
3. aarch64 平台自动检测 ARM64 架构，使用 NEON CRC 加速 (crc32c_arm.c, crc64_arm.c)
4. aws-c-common 的 CMake target 名为 `AWS::aws-c-common`，需通过 CMakeDeps.set_property 设置

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | find_package(aws-c-common) 找不到 | CMakeDeps 默认 target 名不匹配 | set_property cmake_target_name = "AWS::aws-c-common" |
| 2 | include(AwsSIMD) 等模块找不到 | CMakeDeps 不设置 CMAKE_MODULE_PATH | 在 build() 中传入 CMAKE_MODULE_PATH = aws-c-common modules 目录 |

## 结束
status: closed
COMPLETED — aws-checksums 0.2.10 适配完成，conan-verify 全部通过。
# CI trigger
