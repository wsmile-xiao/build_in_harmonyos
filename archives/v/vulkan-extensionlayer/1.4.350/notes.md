# vulkan-extensionlayer 1.4.350 编译笔记

## 编译日期
2026-05-25

## 编译环境
- 系统: HarmonyOS (HongMeng Kernel 1.11.0)
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos-clang++)
- 构建系统: cmake

## 依赖
- VulkanHeaders (vulkan-sdk-1.4.350.0) ✅
- VulkanUtilityLibraries (vulkan-sdk-1.4.350.0) ✅
- VulkanVolk (1.4.350) ✅

## 问题与解决

### 问题1: JSON layer manifest 未安装
**现象**: make install 只安装 .so 文件，不安装 JSON manifest 文件。

**原因**: CMake 在 HarmonyOS 上不设置 UNIX 变量（缺少 Platform/HarmonyOS 模块），导致 layers/CMakeLists.txt 中 `if (UNIX)` 条件为假，跳过了 JSON manifest 安装逻辑。

**解决**: 在 layers/CMakeLists.txt 中将 `if (UNIX)` 改为 `if (UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")`，使 HarmonyOS 系统也能正确安装 JSON layer manifest。

### 问题2: WSI XCB/X11/Wayland 编译依赖
**现象**: cmake 默认启用 WSI 支持，需要 XCB/X11/Wayland pkg-config 模块。

**原因**: CMakeLists.txt 在非 WIN32/ANDROID/APPLE 平台默认启用 WSI 支持。

**解决**: 通过 cmake 选项 `-DBUILD_WSI_XCB_SUPPORT=OFF -DBUILD_WSI_XLIB_SUPPORT=OFF -DBUILD_WSI_WAYLAND_SUPPORT=OFF` 显式禁用。

### 问题3: CMake "System is unknown" 虚告警
**现象**: CMake 打印 "System is unknown to cmake" 信息提示。

**原因**: HarmonyOS 缺少 CMake Platform 模块。

**解决**: 无需处理，仅为信息提示，不影响编译。

## 补丁文件
- 0001-layers-CMakeLists.txt.patch: 将 UNIX 条件扩展为包含 HarmonyOS，以启用 JSON layer manifest 安装

## 编译步骤

### Release 编译
```bash
mkdir build-release && cd build-release
cmake \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
  -DCMAKE_C_COMPILER=/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang++ \
  -DBUILD_WSI_XCB_SUPPORT=OFF \
  -DBUILD_WSI_XLIB_SUPPORT=OFF \
  -DBUILD_WSI_WAYLAND_SUPPORT=OFF \
  -DUPDATE_DEPS=OFF \
  -DBUILD_TESTS=OFF \
  -DCMAKE_PREFIX_PATH=$HOME/usr/local \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  ..
make -j$(nproc)
make install
```

## 生成的 Vulkan Layer

| Layer | .so 文件 | JSON manifest | 说明 |
|-------|----------|---------------|------|
| VK_LAYER_KHRONOS_synchronization2 | libVkLayer_khronos_synchronization2.so | VkLayer_khronos_synchronization2.json | VK_KHR_synchronization2 扩展层 |
| VK_LAYER_KHRONOS_shader_object | libVkLayer_khronos_shader_object.so | VkLayer_khronos_shader_object.json | VK_EXT_shader_object 扩展层 |
| VK_LAYER_KHRONOS_timeline_semaphore | libVkLayer_khronos_timeline_semaphore.so | VkLayer_khronos_timeline_semaphore.json | Timeline semaphore 模拟层 |

## 注意事项
- VkLayer_khronos_memory_decompression 未安装（上游 CMakeLists 明确跳过此层）
- Vulkan-Utility-Libraries 只有 Release 版本的静态库，Debug build 通过 IMPORTED config fallback 使用 Release 静态库
- JSON manifest 中 library_path 使用绝对路径 "libXXX.so"（不含 ./ 前缀），适合系统目录安装