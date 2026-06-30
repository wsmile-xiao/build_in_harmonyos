# Console Bridge

ROS 独立的日志输出库，提供控制台消息输出功能。

## 基本信息

- **主页**: https://github.com/ros/console_bridge
- **许可证**: BSD-3-Clause
- **构建系统**: CMake
- **类别**: library

## 描述

console_bridge 是一个轻量级日志库，提供 ROS 风格的日志输出接口，可独立于 ROS 使用。

## OpenHarmony 适配要点

- 标准 cmake 构建，无特殊适配需求
- 无平台相关代码，纯 C++ 实现
- 无外部依赖

## 可用版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 1.0.2 | published | 2026-06-05 |

## 使用方法

通过 pkg-config 使用：
```bash
pkg-config --cflags console_bridge  # 获取编译选项
pkg-config --libs console_bridge    # 获取链接选项
```

通过 CMake 使用：
```cmake
find_package(console_bridge REQUIRED)
target_link_libraries(your_target console_bridge::console_bridge)
```