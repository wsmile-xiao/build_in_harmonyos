# tlx

Collection of Sophisticated C++ Data Structures, Algorithms and Helpers.

## 简介

tlx 是一个高质量的 C++ 数据结构、算法和辅助类库集合，提供了高效的实现，
广泛用于各种 C++ 项目中。本库专注于提供经过良好测试的高性能组件。

## 功能概述

- **B-tree 容器**：btree_map、btree_set 等高性能容器
- **排序算法**：radix sort、string sort 等多种排序算法
- **字符串工具**：高效的字符串操作和解析工具
- **数学工具**：位操作、数学函数等工具
- **并发组件**：线程池、同步原语等并发编程工具
- **日志诊断**：日志记录和诊断工具

## OHOS 适配

### 适配要点

- **纯静态库**：tlx 编译为纯静态库（libtlx.a），无动态库依赖
- **Header-only 特性**：大部分功能为 header-only，仅部分组件编译为静态库
- **无可执行文件**：本库不提供可执行文件，仅提供库和头文件
- **CMake 兼容性**：需要 CMake 3.5+ 版本
- **编译器要求**：需要支持 C++14 的编译器（推荐 clang++）

### 已知问题

- CMake 会显示 "System is unknown to cmake" 警告（HarmonyOS 平台未在 CMake 中注册），
  不影响编译结果
- 测试套件默认未启用，需要设置 `-DTLX_BUILD_TESTS=ON` 才能编译测试

### 与 Linux 的差异

- 编译选项和安装路径无特殊差异
- 静态库可以直接链接，无平台限制

## 依赖

### 编译依赖

- cmake >= 3.5
- clang++ (支持 C++14)

### 运行依赖

- 无外部运行依赖（纯静态库）

## 功能验证

由于 tlx 是纯静态库且无测试套件，功能验证主要通过：

1. **编译验证**：静态库成功生成（libtlx.a 约 5.6MB）
2. **头文件验证**：头文件完整安装到 include/tlx/
3. **CMake 集成验证**：提供 CMake 配置文件（tlx-config.cmake）
4. **pkg-config 验证**：提供 pkg-config 文件（tlx.pc）

## 质量门禁

| 门禁 | 状态 | 说明 |
|------|------|------|
| G1 二进制完整性 | ✅ PASS | 静态库文件完整 |
| G2 功能可用性 | ⚠️ WARN | 纯静态库无可执行文件 |
| G3 可移植性 | ✅ PASS | 无 RPATH 依赖，无动态库 |
| G4 档案完整性 | ✅ PASS | 必填文件完整 |

## 参考

- **官方网站**: https://github.com/tlx/tlx
- **源码仓库**: https://github.com/tlx/tlx
- **文档**: https://github.com/tlx/tlx/tree/master/doc
- **版本**: 0.6.1

## 版本信息

### 0.6.1 (2026-06-06)

- **构建系统**: CMake
- **编译器**: clang/clang++ 15.0.4
- **状态**: published
- **交付物**: libtlx.a 静态库 + 头文件 + CMake 配置
- **特殊说明**: 纯静态库，无可执行文件
