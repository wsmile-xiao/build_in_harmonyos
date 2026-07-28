# lp_solve — Mixed Integer Linear Programming Solver

## 简介

lp_solve 是一个免费的混合整数线性规划（MILP）求解器，基于修正单纯形法和分支定界法。
它支持纯线性、混合整数/二进制、半连续和特殊有序集（SOS）模型。
lp_solve 使用 LGPL-2.1-or-later 许可证发布。

## 主要特性

- 线性规划（LP）求解
- 混合整数规划（MIP）求解
- 半连续变量支持
- SOS（特殊有序集）支持
- 内置 LUSOL 基分解引擎（默认）
- 支持 LP 和 MPS 文件格式
- 可通过 C API 嵌入其他程序

## 适配版本

| 版本 | 状态 | 构建系统 | 日期 |
|------|------|----------|------|
| 5.5.2.14 | adapted | Conan + generated CMake | 2026-07-27 |

## 当前 Conan 适配

本条目提供 Linux 和 OpenHarmony 消费者可用的 C 库及 `lp_solve`
命令。recipe 根据上游 `ccc` 脚本的源码集合和预处理定义生成 CMake
工程，使编译器、链接器、构建类型和目标架构均由 Conan 配置。

`5.5.2.14` 源码包包含 demo，但没有正式的自动化测试 runner。消费测试
通过公共 C API 求解确定性线性规划、验证命令行程序，并用不存在的模型
文件覆盖失败路径；上游通过率因此记为 N/A，而不是 0/0。

2026-06-09 的旧预编译包流程及其历史补丁记录保留在版本说明中，但这些
补丁未被本次 Conan recipe 引用或应用。
