# OpenXR SDK

OpenXR 是 Khronos Group 开发的开放标准，用于 VR/AR/XR（虚拟现实/增强现实/混合现实）应用的跨平台 API。

## 版本信息

- 版本：1.1.60
- 发布日期：2026-05-21
- 编译日期：2026-06-09
- 状态：built

## 软件简介

OpenXR 提供了一个高性能、低延迟的 API，允许应用程序在各种 XR 设备上运行，无需针对特定设备进行适配。主要包括：

- **OpenXR Loader**：运行时加载器，负责发现和加载 XR 运行时
- **OpenXR API**：标准化的 XR 应用接口
- **API Layers**：可选的中间层，用于调试、性能分析等功能

## OpenHarmony 适配说明

本版本已适配 OpenHarmony 系统，主要修改：

1. **平台识别**：将 HarmonyOS 识别为 Linux-compatible 平台（使用 dlopen/dlclose API）
2. **编译器选择**：使用 OHOS SDK 提供的 clang 15.0.4（系统 clang 18.1.8 缺少运行时库）
3. **图形后端**：添加 "none" backend 选项，支持无图形库的系统

## 安装

### 预编译包安装

```bash
# 从 cmd-pkgs 仓库下载安装脚本
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- openxr 1.1.60
```

### 手动安装

从归档中解压预编译包到 `/storage/Users/currentUser/usr/local`：

```bash
tar xzf openxr-1.1.60-ohos-aarch64.tar.gz -C /storage/Users/currentUser/usr/local
```

## 使用示例

```cpp
#include <openxr/openxr.h>

// 初始化 OpenXR
XrInstance instance;
XrInstanceCreateInfo createInfo = {XR_TYPE_INSTANCE_CREATE_INFO};
xrCreateInstance(&createInfo, &instance);

// 创建会话
XrSession session;
XrSessionCreateInfo sessionCreateInfo = {XR_TYPE_SESSION_CREATE_INFO};
xrCreateSession(instance, &sessionCreateInfo, &session);
```

### pkg-config

```bash
# 查询版本
pkg-config --modversion openxr
# 输出：1.1.60

# 查询编译标志
pkg-config --cflags openxr
# 输出：-I/storage/Users/currentUser/usr/local/include/openxr

# 查询链接标志
pkg-config --libs openxr
# 输出：-L/storage/Users/currentUser/usr/local/lib -lopenxr_loader
```

### CMake 集成

```cmake
find_package(OpenXR REQUIRED)
target_link_libraries(your_target OpenXR::Loader)
```

## 依赖

- clang 15.0.4 (OHOS SDK)
- cmake 4.1.2+

## 已知限制

1. **无图形支持**：当前版本禁用了图形 backend（PRESENTATION_BACKEND=none），仅提供 loader 功能
2. **编译器限制**：必须使用 OHOS SDK 提供的 clang，用户编译的 clang 可能缺少运行时库
3. **测试禁用**：为减少依赖，禁用了测试和示例程序

## 相关资源

- 官方网站：https://www.khronos.org/openxr/
- 源码仓库：https://github.com/KhronosGroup/OpenXR-SDK
- 文档：https://www.khronos.org/registry/OpenXR/specs/1.0/html/xrspec.html

## 许可证

Apache 2.0 或 MIT（双许可）

## 维护者

OpenHarmony 编译团队

## 更新历史

- 2026-06-09：完成 OpenHarmony 适配，生成预编译包
- 2026-05-21：上游发布 1.1.60 版本