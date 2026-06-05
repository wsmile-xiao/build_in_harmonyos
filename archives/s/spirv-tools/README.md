# spirv-tools

SPIRV-Tools - SPIR-V 二进制模块的优化器、验证器和汇编器/反汇编器工具集。

## 版本历史

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| vulkan-sdk-1.3.290.0 | built | 2026-05-19 |

## 描述

SPIRV-Tools 是 KhronosGroup 开发的 SPIR-V 工具集，包含：

- **spirv-as**: SPIR-V 汇编器
- **spirv-dis**: SPIR-V 反汇编器
- **spirv-val**: SPIR-V 验证器
- **spirv-opt**: SPIR-V 优化器
- **spirv-link**: SPIR-V 链接器
- **spirv-reduce**: SPIR-V 精简器
- **spirv-lint**: SPIR-V 检查器

## 依赖

- **spirv-headers** (vulkan-sdk-1.3.290.0): 必需，SPIR-V 头文件

## 使用方法

```bash
# 反汇编 SPIR-V 二进制
spirv-dis input.spv -o output.spvasm

# 验证 SPIR-V 模块
spirv-val input.spv

# 优化 SPIR-V 模块
spirv-opt -O input.spv -o optimized.spv
```

## 构建系统

CMake，需在 `external/` 目录放置 spirv-headers 源码。

## 平台适配

HarmonyOS 平台需添加 CMakeLists.txt 补丁（0001-CMakeLists.txt.patch），将 HarmonyOS 作为 Linux 处理。

## 归档位置

`archives/s/spirv-tools/vulkan-sdk-1.3.290.0/`