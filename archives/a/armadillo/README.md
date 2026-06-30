# Armadillo

## 简介

Armadillo 是一个高质量 C++ 线性代数库，旨在在速度和易用性之间取得良好的平衡。它提供了类似 Matlab 语法的 API，适合科学计算、机器学习和计算机视觉应用。

## 功能特性

- 矩阵和向量运算
- 线性代数运算（求解线性方程组、特征值分解、SVD 等）
- 统计函数
- 支持 BLAS 和 LAPACK 加速
- 头文件友好设计

## 编译版本

- **当前版本**: 12.8.4
- **构建系统**: CMake
- **编译选项**: `-DBUILD_SHARED_LIBS=ON`
- **编译器**: Clang

## 编译产物

- `lib/libarmadillo.so` - 共享库
- `lib/pkgconfig/armadillo.pc` - pkg-config 配置文件
- `include/armadillo` - 主头文件
- `include/armadillo_bits/` - 内部头文件
- `share/Armadillo/CMake/` - CMake 配置文件

## 注意事项

1. 默认编译为共享库（.so），需要显式指定 `-DBUILD_SHARED_LIBS=ON`
2. 无外部 BLAS/LAPACK 依赖时，功能受限但仍可编译成功
3. configure 脚本只是 CMake wrapper，实际使用 CMake 构建系统

## 链接

- 官网: http://arma.sourceforge.net/
- 源码: https://sourceforge.net/projects/arma/