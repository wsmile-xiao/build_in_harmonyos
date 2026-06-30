# CMinpack

## 软件描述
CMinpack 是 MINPACK 非线性优化库的 C 语言重写版本。MINPACK 最初由 Argonne National Laboratory 开发，包含用于求解非线性方程组和最小二乘问题的算法。

## 主要功能
- **Hybrid 方法** (hybrd/hybrj): 求解非线性方程组
- **Levenberg-Marquardt 方法** (lmder/lmdif): 最小二乘优化
- **Jacobian 计算** (fdjac): 前向/中心差分近似
- **导数检查** (chkder): 验证解析导数正确性

## 精度变体
- `libcminpack_s.a`: 双精度 (double)
- `libcminpacks_s.a`: 单精度 (float)
- `libcminpackld_s.a`: 长双精度 (long double)

## 构建信息
- 构建系统: CMake
- 编译器: Clang 15.0.4
- 平台: HarmonyOS (aarch64)
- 编译选项: 静态库 + Release + 无 BLAS

## 版本
- 1.3.9 (2026-06-24): 鸿蒙预编译版本
