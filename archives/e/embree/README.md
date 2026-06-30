# Embree

## 简介

Embree 是 Intel 开发的高性能光线追踪内核库，为渲染器、游戏引擎和科学可视化应用提供优化的光线追踪算法实现。

## 主要功能

- **BVH 构建**：高效的层次包围盒（BVH）构建算法
- **光线相交**：三角形、四边形、曲线、点云等多种几何体的光线相交测试
- **运动模糊**：支持时间和几何运动模糊
- **实例化**：支持多层实例化场景
- **细分曲面**：支持 Catmull-Clark 细分曲面
- **用户几何体**：支持自定义几何体相交函数

## HarmonyOS 适配

### 适配要点

1. **架构支持**：Embree v4.4.1 支持 ARM64 架构和 NEON SIMD 指令集
2. **静态库编译**：必须编译为静态库（`-DEMBREE_STATIC_LIB=ON`），动态库在 HarmonyOS 上有 libc++ 链接问题
3. **ISA 配置**：必须明确设置 ARM 和 NEON：
   ```
   -DEMBREE_ARM=ON
   -DEMBREE_ISA_NEON=ON
   -DEMBREE_ISA_SSE2=OFF
   -DEMBREE_ISA_SSE42=OFF
   -DEMBREE_ISA_AVX=OFF
   -DEMBREE_ISA_AVX2=OFF
   ```
4. **Tasking System**：使用内部线程系统（`-DEMBREE_TASKING_SYSTEM=INTERNAL`）避免依赖 TBB
5. **禁用 Tutorials**：glfw 不支持 HarmonyOS，必须禁用 tutorials（`-DEMBREE_TUTORIALS=OFF`）

### 平台差异

| 功能 | Linux x86 | HarmonyOS ARM | 说明 |
|------|-----------|---------------|------|
| SIMD 指令 | SSE/AVX/AVX2 | NEON | Embree v4 支持 ARM NEON |
| 线程亲和性 | pthread_setaffinity_np | sched_setaffinity | HarmonyOS 使用 sched API |
| pthread_cancel | 支持 | 不支持 | 禁用线程销毁功能 |
| 动态库 | 支持 | 不推荐 | 使用静态库避免 libc++ 问题 |

### 已知问题

1. **无 TBB 预编译包**：HarmonyOS 上没有 TBB 预编译包，使用 INTERNAL tasking system
2. **glfw 不支持**：HarmonyOS 没有 glfw 支持，无法运行 tutorials
3. **无测试验证**：测试套需要运行环境，无法在编译阶段验证功能

## 依赖关系

### 编译依赖

- **无外部依赖**：使用 INTERNAL tasking system，不依赖 TBB
- **pthread**：系统线程库（必需）

### 运行依赖

- 无运行依赖（静态库编译）

## 使用方法

### CMake 配置

```cmake
find_package(embree REQUIRED)
target_link_libraries(your_target embree)
```

### 编译选项

关键编译选项：

- `EMBREE_TASKING_SYSTEM=INTERNAL`：使用内部线程系统
- `EMBREE_STATIC_LIB=ON`：编译为静态库
- `EMBREE_ARM=ON`：启用 ARM 支持
- `EMBREE_ISA_NEON=ON`：启用 NEON SIMD
- `EMBREE_TUTORIALS=OFF`：禁用 tutorials

## 参考资料

- 官网：https://embree.github.io/
- GitHub：https://github.com/RenderKit/embree
- 文档：https://embree.github.io/api.html
- 版本：4.4.1（支持 ARM64）