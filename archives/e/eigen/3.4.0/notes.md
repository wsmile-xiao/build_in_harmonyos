# eigen 3.4.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-15
- 编译器: clang 15.0.4 / clang++
- 平台: HarmonyOS (aarch64)
- 状态: published (conan-verify 通过)

## 编译步骤
1. 下载并解压 eigen 3.4.0 源码
2. CMake 配置 (BUILD_TESTING=OFF, EIGEN_BUILD_TEST=OFF, EIGEN_BUILD_BTL=OFF)
3. cmake build (header-only 库，无编译产物)
4. cmake install (安装头文件到 include/eigen3/)
5. 无需补丁

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| - | 无重大问题 | Header-only 库，原生兼容 | - |

## 依赖版本
- 无外部依赖（header-only）

## 注意事项
- Eigen 是 header-only C++ 模板库，不产生 .a/.so 二进制文件
- conanfile.py 使用 package_type = "header-library"
- package_info() 中 libs = []，includedirs = ["include/eigen3"]
- test_package 使用 C++ 测试矩阵-向量乘法验证 Eigen API
- 设置 CMake 属性 Eigen3::Eigen 和 cmake_file_name Eigen3 以匹配上游 CMake 配置

---

**编译结束**: 2026-07-15
**最终状态**: published
