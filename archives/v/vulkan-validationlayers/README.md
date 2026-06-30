# vulkan-validationlayers

Vulkan Validation Layers (VVL) - Vulkan API 验证层，用于检测 Vulkan API 使用中的错误。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| vulkan-sdk-1.4.350.0 | built | Vulkan SDK 1.4.350.0 版本 |

## 描述

Vulkan Validation Layers 是 Khronos Group 维护的 Vulkan API 验证层，提供全面的 API 使用验证，
包括参数验证、对象生命周期追踪、线程安全检查、同步验证和最佳实践建议。

## 编译要点

- 构建系统: cmake
- OpenHarmony 适配: 需要 CMAKE_SYSTEM_NAME=Linux 和禁用 WSI 支持
- 依赖: Vulkan-Headers (匹配版本), SPIRV-Headers, SPIRV-Tools-opt, Vulkan-Utility-Libraries
