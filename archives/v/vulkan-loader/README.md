# vulkan-loader 软件归档

## 软件
Vulkan Loader - Vulkan 运行时加载器

## 描述
Vulkan Loader 是 Vulkan API 的核心组件，负责发现和加载 Vulkan 驱动(ICD)，以及处理 Vulkan 层(Layer)的加载。

## 编译版本
- 1.3.295

## 构建系统
- CMake

## 关键依赖
- Vulkan Headers (同版本)

## 平台适配
- HarmonyOS 使用 CMAKE_SYSTEM_NAME=Linux
- 关闭所有 WSI 支持（XCB/Xlib/Wayland/DirectFB）

## 归档日期
2026-05-21