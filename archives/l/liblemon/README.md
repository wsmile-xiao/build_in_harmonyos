# liblemon

## 简介

LEMON (Library for Efficient Modeling and Optimization in Networks) is a C++
library for graph structures, graph algorithms, and network optimization.

## OHOS 适配

- 使用上游 CMake 构建并保留 pthread 支持。
- 关闭 GLPK、CPLEX、COIN-OR 和 SoPlex 可选后端，保持基础图算法包无第三方依赖。
- 构建并执行无求解器配置下的完整 42 项上游 CTest。
- 安装 `lgf-gen`、`dimacs-to-lgf` 和 `dimacs-solver` 三个命令行工具。

## 依赖

- 仅使用 C/C++ 运行时和 pthread 系统能力。

## 功能验证

- 上游 CTest: 42/42。
- Conan 消费者实际链接 `libemon`，验证有向图、BFS 和全局随机数 API。

## 参考

- https://lemon.cs.elte.hu/

