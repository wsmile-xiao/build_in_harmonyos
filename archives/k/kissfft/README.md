# KISS FFT

## 简介

KISS FFT 是一个轻量级的快速傅里叶变换（FFT）库，遵循"Keep It Simple, Stupid"原则。它是一个纯 C 语言实现的数学运算库，专注于提供简单、高效且易于集成的 FFT 功能。

## 功能特性

- 支持 1D 复数 FFT
- 支持实数 FFT
- 支持固定点（int16/int32）和浮点数据类型
- 支持 SIMD 优化（可选）
- 多基数 FFT 混合实现
- 可配置为静态库或动态库
- 提供工具程序（fft 工具）

## OHOS 适配要点

- **纯数学运算库**：无平台特定代码，无需特殊适配
- **构建系统**：支持 Makefile 和 CMake，推荐使用 Makefile
- **编译参数**：只需指定 PREFIX，无需其他 configure 参数
- **数据类型**：默认使用 float，可通过环境变量切换
- **无外部依赖**：完全独立，不依赖其他库

## 编译依赖

无编译依赖，纯 C 语言实现。

## 运行依赖

无运行依赖。

## 参考资料

- 官方仓库：https://github.com/mborgerding/kissfft
- 文档：README.md（源码包内）
- 许可证：BSD-3-Clause / Unlicense（双许可）