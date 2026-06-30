# NLopt

## 简介
NLopt 是一个开源的非线性优化库，提供了多种全局和局部优化算法。

## 主要功能
- 全局优化算法：DIRECT, CRSA, MLSL, StoGO 等
- 局部优化算法：MMA, SLSQP, COBYLA, NEWUOA 等
- 支持有约束和无约束优化问题
- 提供 C/C++/Python/Java 等多语言接口

## 编译信息
- 版本: 2.10.1
- 构建系统: CMake
- 编译器: Clang 15.0.4

## 依赖
- 无外部依赖（纯数学库）

## 使用方式
```bash
# 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- nlopt 2.10.1

# CMake 项目使用
find_package(NLopt REQUIRED)
target_link_libraries(your_target PRIVATE nlopt)
```

## 文件结构
- lib/libnlopt.so - 共享库
- include/nlopt.h - C API 头文件
- include/nlopt.hpp - C++ API 头文件
