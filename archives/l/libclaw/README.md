# libclaw

Claw ("C++ Library Absolutely Wonderful") 是一个通用 C++ 库, 提供容器、补间动画、二维几何、图像读写 (bmp/jpeg/png/pcx/targa/xbm)、网络套接字、配置文件解析与日志等能力, 常用于游戏项目 (如 Plee the Bear)。

## 描述

上游: https://libclaw.sourceforge.net/ (SourceForge), 镜像: https://github.com/j-jorge/libclaw

## 已编译版本

- 1.7.4 (2026-09-18)

## 特性

- 补间动画 (tween) 与缓动函数
- 二维几何 (box_2d/rectangle/point/vector)
- 图像读写 (jpeg/png 由系统库提供)
- 配置文件、日志、动态库、网络套接字

## 使用方法

```cmake
find_package(libclaw REQUIRED CONFIG)
target_link_libraries(app PRIVATE libclaw::libclaw)
```
