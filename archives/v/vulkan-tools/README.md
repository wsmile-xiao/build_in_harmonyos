# Vulkan Tools

## 简介
Vulkan Development Tools - Vulkan 开发工具集，包括 vulkaninfo（信息查询工具）和 Mock ICD（测试驱动）。

## OHOS 适配
- **平台识别**: CMake 需要设置 `CMAKE_SYSTEM_NAME=Linux`，因为 HarmonyOS 基于 Linux 内核
- **WSI 支持**: 禁用所有 Window System Integration 支持（XCB/Xlib/Wayland/DirectFB），HarmonyOS 不使用 X11
- **ICD 安装**: 默认不安装 Mock ICD，需要启用 `INSTALL_ICD=ON` 选项
- **构建系统**: cmake

## 排除与替代
- `BUILD_CUBE` 禁用：cube demo 需要 xcb，HarmonyOS 不支持
- `BUILD_WSI_*` 全部禁用：无 X11/Wayland 环境

## 依赖
- vulkan-headers (>= 1.3.290)
- volk (>= 1.3.290)

## 功能验证
```bash
vulkaninfo --summary  # 查看 Vulkan 设备信息
```

## 参考
- 官方仓库: https://github.com/KhronosGroup/Vulkan-Tools
- Vulkan 文档: https://vulkan.lunarg.com/