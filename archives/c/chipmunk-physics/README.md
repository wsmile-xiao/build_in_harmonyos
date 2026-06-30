# chipmunk-physics

## 软件描述

Chipmunk2D 是一个快速、轻量的 2D 刚体物理引擎库，用 C 语言编写。由 Scott Lembcke 开发，广泛应用于游戏开发和其他需要物理模拟的场景。

主要特性：
- 2D 刚体物理模拟（碰撞检测、关节约束、力学模拟）
- 支持静态库和共享库两种构建模式
- 多线程求解器（cpHastySpace，基于 pthread）
- 自动几何体生成（cpMarch）
- 纯 C 实现，无外部运行时依赖

## 构建系统

- 构建系统：CMake
- 语言：C (C99)
- 最低 CMake 版本：3.7

## 编译版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 7.0.3 | published | 2026-06-18 | 初始编译，修复 sys/sysctl.h 平台兼容性 |

## 源码

- 上游仓库：https://github.com/slembcke/Chipmunk2D
- 官方网站：https://chipmunk-physics.net/

## 依赖

无外部运行时依赖。构建时需要 CMake 和 C 编译器（clang/gcc）。
