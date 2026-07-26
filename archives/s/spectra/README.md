# Spectra

Spectra 是一个基于 Eigen 的 C++ 模板库，用于求解大规模稀疏/稠密矩阵的特征值问题。它提供了类似于 ARPACK 的功能，但接口更现代、更易用。

## 功能概述
- 对称/厄米矩阵特征值求解 (SymEigsSolver, SymEigsShiftSolver)
- 一般矩阵特征值求解 (GenEigsSolver, GenEigsShiftSolver)
- Davidson 方法 (DavidsonSymEigsSolver)
- Bunch-Kaufman LDLT 分解
- 仅依赖 Eigen (header-only), 无需编译库文件
- 支持 C++11 及以上标准

## OHOS 适配
- Header-only 库 (CMake INTERFACE 目标), 无需编译库文件
- 依赖 Eigen 3.4.0, 通过 CPM.cmake 自动下载 (Eigen 不在 Conan 注册表中)
- 需设置 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64` (OHOS 平台适配)
- Eigen 头文件一并打包到 `include/eigen3/` 子目录

## 依赖关系
- **编译依赖**: Eigen 3.4.0 (由 CPM.cmake 自动下载, header-only)
- **运行依赖**: 无

## 参考资料
- 官网: https://github.com/yixuan/spectra
- 文档: https://spectralib.org/doc
