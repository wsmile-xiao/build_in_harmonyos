# open-mesh

Generic data structure to represent and manipulate polygonal meshes.

## 描述

OpenMesh 是一个通用的多边形网格数据结构库，提供表示和操作三角/多边形网格的 C++ 框架。支持半边数据结构，包含网格 I/O（OBJ/OFF/PLY/OM/STL/VTK）、网格简化（Decimater）、网格平滑（Smoother）、网格细分（Subdivider）等工具模块。

## 许可证

BSD-3-Clause

## 编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 11.0.0 | published | 2026-06-10 |

## 主要产物

- 库文件: libOpenMeshCore.so, libOpenMeshCore.a, libOpenMeshTools.so, libOpenMeshTools.a
- 工具: Dualizer, commandlineDecimater, Smoothing, commandlineSubdivider, commandlineAdaptiveSubdivider, mconvert, mkbalancedpm, Analyzer
- 头文件: OpenMesh/Core/ 和 OpenMesh/Tools/ 全套 C++ 头文件