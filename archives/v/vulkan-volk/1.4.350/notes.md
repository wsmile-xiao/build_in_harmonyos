# vulkan-volk 1.4.350 编译笔记

## 编译日期
2026-05-25

## 编译环境
- 系统: HarmonyOS (HongMeng Kernel 1.12.0)
- 编译器: clang 15.0.4
- 构建系统: CMake 4.1.2

## 依赖
- VulkanHeaders (vulkan-sdk-1.4.350.0) ✅

## 问题与解决

### 问题1: CMake "Unknown system" 警告
**现象**: CMake 打印 "System is unknown to cmake" 警告，因为 CMake 内置模块中没有 `Platform/HarmonyOS.cmake`。

**原因**: CMake 的系统检测机制在 `project()` 调用时尝试加载 `Platform/${CMAKE_SYSTEM_NAME}.cmake`，找不到时会发出警告并回退到 Generic 平台。

**解决**: 创建 `cmake/Platform/HarmonyOS.cmake` 文件，并在 CMakeLists.txt 中将项目 cmake 目录添加到 `CMAKE_MODULE_PATH`，使 CMake 在系统检测时能找到此 Platform 文件。

### 问题2: VK_USE_PLATFORM_OHOS 未自动定义
**现象**: volk.h 的 header-only 模式默认只包含 `vulkan/vk_platform.h` 和 `vulkan/vulkan_core.h`，不包含 OHOS 平台专用的 `vulkan/vulkan_ohos.h`。

**原因**: volk.h 使用条件编译机制，只有当 `VK_USE_PLATFORM_OHOS` 宏被定义时才包含 `<vulkan/vulkan_ohos.h>`。CMakeLists.txt 中的 `VOLK_STATIC_DEFINES` 选项需要手动设置或自动检测。

**解决**: 在 CMakeLists.txt 中，当 `CMAKE_HOST_SYSTEM_NAME=HarmonyOS` 时，自动设置 `VOLK_STATIC_DEFINES=VK_USE_PLATFORM_OHOS`。注意使用 `CMAKE_HOST_SYSTEM_NAME`（在 `project()` 之前可用）而非 `CMAKE_SYSTEM_NAME`（仅在 `project()` 之后设置）。

## 补丁文件
- 0001-CMakeLists.txt.patch: 添加 CMAKE_MODULE_PATH + CMAKE_HOST_SYSTEM_NAME=HarmonyOS 自动检测
- 0002-cmake-Platform-HarmonyOS.cmake.patch: 创建 Platform/HarmonyOS.cmake 以消除 Unknown 系统警告

## 制品
- libvolk.a (静态库)
- volk.h (头文件)
- volk.c (实现文件，以 include 形式安装)

## 注意事项
- volk 是纯静态库，无可执行二进制，G1/G2 门禁为空属正常
- volk.c 使用 dlopen/dlsym 加载 Vulkan loader，与 Linux/POSIX 路径一致
---

**编译结束**: 2026-08-30 00:59
**最终状态**: built

