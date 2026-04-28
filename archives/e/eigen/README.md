# Eigen

Eigen 是一个高性能的 C++ 模板库，用于线性代数、矩阵和向量运算、数值求解以及相关算法。

## 功能概述
- 矩阵和向量运算（固定/动态大小）
- 稀疏矩阵支持
- 几何变换（旋转、仿射变换等）
- 数值求解（LU、QR、SVD、特征值等）
- SIMD 自动向量化
- Header-only，无需编译库文件

## OHOS 适配
- Header-only 库，核心功能无需编译
- CMake 安装过程简单
- 无需补丁即可在 HarmonyOS 上编译安装

## 依赖关系
- **编译依赖**: 无（header-only）
- **运行依赖**: 无

## 参考资料
- 官网: https://eigen.tuxfamily.org/
- 源码: https://gitlab.com/libeigen/eigen
