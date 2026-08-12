# M4RI

## 简介
M4RI（Method of Four Russians Inversion）是 GF(2)（二元域）上的稠密矩阵运算库，
提供矩阵乘法、消元、求秩等操作。SageMath / passagemath 计算代数栈的底层依赖。

## 基本信息
- 官网: https://github.com/malb/m4ri
- 源码: https://github.com/malb/m4ri/releases
- 许可证: GPL-2.0-or-later
- 构建系统: autotools

## 已编译版本
- 20260122 (2026-08-12)

## 依赖
- libpng —— `m4ri/io.c` 无条件 `#include <png.h>`，上游未做成可选项

## 使用方式
```bash
conan install --requires=m4ri/20260122 -pr ohos-native
clang your_program.c -lm4ri
```
