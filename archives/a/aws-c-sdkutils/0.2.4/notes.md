# aws-c-sdkutils 0.2.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-09
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤
标准 CMake 构建，通过 Conan 管理依赖。

### Conan 配方
- conanfile.py 生成，依赖 aws-c-common/0.14.3
- CMakeDeps 设置 cmake_target_name="AWS::aws-c-common" 以匹配 AWS CMake 模块
- CMAKE_MODULE_PATH 指向 aws-c-common 的 CMake 模块目录
- conan-verify 全部通过 (G1/G2/G3/G4)

### 测试
- test_package 使用前向声明 API 避免 aws-c-common 头文件依赖
- 测试 aws_sdkutils_library_init/clean_up 函数调用
- 对标上游测试: tests/sdkutils_test.c

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aws-c-common/0.12.6 不在制品仓 | 上游版本未发布 | 改用 aws-c-common/0.14.3 |
| 2 | test_package 编译失败: 'aws/common/common.h' not found | aws-c-common 包的 CMakeDeps INCLUDE_DIRS 为空 | 前向声明 API，显式 find_package + link aws-c-common |
| 3 | CMake 找不到 aws-c-common | 需 AWS CMake 模块和 AWS:: target | CMakeDeps set_property + CMAKE_MODULE_PATH |

## 最终状态

COMPLETED — aws-c-sdkutils 0.2.4 适配完成，状态: built
