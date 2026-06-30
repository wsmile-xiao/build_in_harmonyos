# fastfetch

## 软件简介

fastfetch 是一个类似于 neofetch 的系统信息显示工具，使用 C 语言编写，性能更好且支持更多特性。它能快速显示系统信息，包括操作系统、内核、CPU、GPU、内存等。

## 主要特性

- 快速的系统信息获取（比 neofetch 更快）
- 支持多种输出格式（文本、JSON）
- 丰富的自定义选项和配置文件支持
- 支持多种操作系统和架构
- 低内存占用

## 编译版本

### 2.63.1

- **状态**: built
- **编译日期**: 2026-05-22
- **归档路径**: archives/f/fastfetch/2.63.1/

## 编译说明

fastfetch 使用 CMake 构建系统，在 HarmonyOS 平台上需要以下适配：

1. CMake 平台检测适配（CMakeLists.txt 修改）
2. 用户检测模块适配（users_linux.c）

详见版本级 notes.md。