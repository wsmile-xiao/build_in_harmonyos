# aws-c-cal 0.9.13 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-08-05
- 编译器: clang/clang++
- 状态: success

## 编译步骤
1. 下载源码 aws-c-cal-0.9.13.tar.gz
2. CMake 配置（静态库，禁用测试）
3. 编译生成静态库 libaws-c-cal.a
4. 安装到 staging 目录

## 依赖
- aws-c-common/0.12.6: AWS SDK 核心库
- aws-lc/5.4.0: AWS libcrypto，作为 crypto 后端

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | find_package(crypto) 找不到 | aws-lc 的 Conan 包名为 aws-lc，但 CMakeLists.txt 调用 find_package(crypto) | 在 generate() 中通过 CMakeDeps.set_property 设置 cmake_file_name=crypto, cmake_target_name=AWS::crypto |
| 2 | include(AwsCFlags) 失败 | aws-c-common 的 CMake 模块在 lib/cmake/aws-c-common/modules/，CMakeDeps 不自动添加到 CMAKE_MODULE_PATH | 在 build() 中通过 cmake.configure(variables={"CMAKE_MODULE_PATH": ...}) 传入 |
| 3 | AWS::aws-c-common target not found | CMakeDeps 默认生成 aws-c-common::aws-c-common，但 CMakeLists.txt 期望 AWS::aws-c-common | 通过 CMakeDeps.set_property 设置 cmake_target_name=AWS::aws-c-common |

## 验证结果
- 产物为纯静态库 libaws-c-cal.a
- conan-verify 全部通过 (G1-G4, L2/L4/L5)

## 注意事项
- aws-c-common 和 aws-lc 的 conanfile.py 缺少 cpp_info.includedirs 声明，需要单独修复
- 测试用例使用前向声明避免依赖 aws-c-common 头文件
---

**编译结束**: 2026-08-05 05:07
**最终状态**: built
