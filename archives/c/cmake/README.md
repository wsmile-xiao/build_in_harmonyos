# CMake

CMake 是一个跨平台的构建系统生成器，用于管理构建过程。

## 功能概述

- 生成 Makefile、Ninja、Visual Studio 等多种构建系统
- 跨平台 C/C++ 项目管理
- 支持 out-of-source 构建
- 丰富的 FindXXX 模块
- CPack 打包和 CTest 测试集成

## OHOS 适配

- 构建系统为 cmake（bootstrap）
- 需要设置 CMAKE_SYSTEM_NAME=OHOS
- Bootstrap 阶段需要 --no-qt-gui

## 依赖关系

- C/C++ 编译器
- OpenSSL（可选）
- curl（可选）

## 参考资料

- 官网: https://cmake.org/
- 源码: https://github.com/Kitware/CMake
