# FFLAS-FFPACK

## 简介
Finite Field Linear Algebra Subroutines / Package —— 有限域上的稠密线性代数库，
提供矩阵乘法、消元、求秩、解方程等。**header-only**。
是 LinBox、SageMath / passagemath 计算代数栈的核心依赖。

## 基本信息
- 官网: https://github.com/linbox-team/fflas-ffpack
- 源码: https://github.com/linbox-team/fflas-ffpack/releases
- 许可证: LGPL-2.1-or-later
- 构建系统: autotools

## 已编译版本
- 2.5.0 (2026-08-12)

## 依赖
包本身只装头文件，但头文件里直接调用以下两者：
- givaro/4.2.1（有限域运算）
- openblas（BLAS 后端，经 `--with-blas-libs`）

## 使用方式
```bash
conan install --requires=fflas-ffpack/2.5.0 -pr ohos-native
```
