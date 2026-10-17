# ADIOS2

ADIOS2 是面向高性能计算、科学计算和数据分析场景的可扩展并行 I/O 框架。

## 功能概述

- 提供 C 和 C++ 数据读写接口
- 支持 BP 文件格式
- 支持变量、属性和多维数组
- 提供可扩展的引擎与传输架构

## OHOS 适配

- 构建串行 C/C++ 核心静态库
- 使用 C++17
- 使用上游内置的基础解析依赖
- 暂不启用 MPI、Fortran、Python、SST、HDF5 和可选压缩后端

## 依赖关系

- 编译依赖：CMake、C/C++ 编译器
- 运行依赖：pthread、dl

## 参考资料

- 文档：https://adios2.readthedocs.io
- 源码：https://github.com/ornladios/ADIOS2
