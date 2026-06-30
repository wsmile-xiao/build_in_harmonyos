# ABySS

## 简介

ABySS (Assembly by Short Sequences) 是一个用于短读长配对端测序数据的从头序列组装工具，适用于各种大小的基因组组装。

## 功能概述

- **de Bruijn 图组装**: 使用 de Bruijn 图算法进行序列组装
- **Bloom 过滤器模式**: 显著降低内存消耗（可减少 10 倍）
- **多线程支持**: 支持 OpenMP 多线程并行处理
- **MPI 分布式计算**: 支持多机分布式组装（传统模式）
- **配对端 scaffolding**: 利用配对端测序信息进行支架构建
- **多库支持**: 支持多个测序库的同时组装
- **Linked reads 支持**: 支持 10x Genomics linked reads 进行支架构建

## OHOS 适配要点

### 平台限制

1. **HMDFS 文件系统**:
   - configure 脚本动态创建临时目录受限
   - 需修改 config.status 使用 ./tmp_files 替代硬编码路径

2. **POSIX 信号量不支持**:
   - 鸿蒙系统不支持 `sem_t` 类型
   - 需使用 pthread 条件变量替代

3. **fopen64/fopen 宏定义冲突**:
   - 鸿蒙系统中 `fopen64` 被定义为 `fopen`
   - 需添加条件编译防止重复定义

4. **C++17 兼容性**:
   - `std::iterator` 已弃用
   - `std::random_shuffle` 已移除
   - 需替换为现代 API

### 依赖处理

- **btllib**: 需手动编译（预编译包不存在）
- **sparsehash**: 使用预编译包
- **boost/openmpi**: 系统已预装

## 依赖关系

### 编译依赖
- **autoconf** >= 2.71
- **automake** >= 1.16.5
- **C++ 编译器** (支持 C++17 和 OpenMP)
- **boost** >= 1.56
- **Open MPI** >= 4.1
- **sparsehash** >= 2.0.4
- **btllib** >= 1.4.1

### 可选依赖
- **SQLite** (用于数据库导出)
- **ARCS** (linked reads scaffolding)
- **Tigmint** (linked reads 错误修正)

## 参考资料

- **GitHub**: https://github.com/BirolLab/abyss
- **文档**: https://github.com/BirolLab/abyss/blob/master/README.md
- **论文**: Simpson et al. (2009) ABySS: a parallel assembler for short read sequence data. Genome Res. 19:1117-1123.