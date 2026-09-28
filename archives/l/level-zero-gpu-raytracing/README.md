# Level Zero GPU Ray Tracing (level-zero-gpu-raytracing)

oneAPI Level Zero Ray Tracing Support —— 为 Level Zero 的 `ZE_extension_rtas` 扩展提供
CPU 侧光线追踪加速结构 (RTAS) 构造实现。

- 上游仓库: <https://github.com/intel/level-zero-raytracing-support>
- 许可证: Apache-2.0
- 构建系统: CMake
- 上游发行说明: <https://github.com/intel/level-zero-raytracing-support/releases>

## 这个库做什么

Level Zero 是 Intel oneAPI 面向加速器（GPU 等）的底层统一 API。本库实现其中的
`ZE_extension_rtas`（以及已废弃的实验性 `ZE_experimental_rtas_builder`）：

> 在 CPU 上执行高性能的光线追踪加速结构（RTAS）构造算法，输入来自上述 API，
> 产出与 Intel GPU 光追硬件兼容的 RTAS。

**应用不直接链接本库。** 应用链接 Level Zero loader (`libze_loader`)，通过 loader 使用
`ZE_extension_rtas` API；loader 按驱动上报的扩展能力在运行时加载本库。因此本库的
CMake 版本脚本（`rtbuild/export.linux.map`）只导出 `ze*` 符号，供 loader 动态解析。

内部结构：

| 目录 | 作用 |
|------|------|
| `rtbuild/` | CPU 侧 QBVH6 加速结构构建算法、几何处理、统计 |
| `rtbuild/simd/` | 4 宽向量层（上游为 SSE2 实现） |
| `level_zero/` | `ze_wrapper`：运行时以 `dlopen`/`dlsym` 解析 loader 的薄封装 |
| `testing/` | 需要 DPC++ 与 Intel Xe 设备的硬件测试套件 |

## 版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 1.2.3 | built | 2026-09-26 | 首次适配；aarch64 向量层经 SSE2 仿真层接入 |

## HarmonyOS PC (aarch64) 适配要点

1. **SSE2 → aarch64**：上游向量层只有 SSE2 实现（`vfloat4_sse2.h` 等，共 94 个
   `_mm_*` intrinsic）。aarch64 上由 `sse2neon`（头文件级仿真层）提供 SSE2 API，
   **不改动上游算法代码**。
2. **`<immintrin.h>` 不可用**：`rtbuild/sys/intrinsics.h` 无条件包含该头，aarch64 上
   直接 `#error`。按架构守卫。
3. **上游 ARM 路径缺文件**：`rtbuild/math/emath.h` 引用 `simd/arm/emulation.h`，
   该文件在已发布源码中不存在（属上游从未发布的实现）。
4. **`__64BIT__` 仅对 x86 检测**：导致 aarch64 上缺 `size_t` 重载，`min()` 调用歧义。
5. **TBB 来源**：上游默认 `build_static` 会在 configure 期间 `git clone` oneTBB，
   不可复现且需网络；改用制品仓 TBB（`ZE_RAYTRACING_TBB=normal`）。
6. **CMake 4.x**：上游 `cmake_minimum_required(3.1.0)` 需配合
   `CMAKE_POLICY_VERSION_MINIMUM=3.5`。

详细的根因、补丁说明与实测数据见 [`1.2.3/notes.md`](1.2.3/notes.md)。

## 验证边界（重要）

本库属图形渲染 / 系统底层类（R40）。当前适配环境**没有 Intel Xe GPU 与 Level Zero
内核态驱动**，因此：

| 项目 | 状态 |
|------|------|
| 编译 / 链接 | ✅ 已验证 |
| 库可加载、导出符号完整 | ✅ 已验证（`dlsym` 断言） |
| API 校验与格式比较逻辑行为 | ✅ 已验证（互斥结果码断言） |
| 上游硬件测试套件 (56 个 ctest 用例) | ❌ 本平台不可构建：需 `-fsycl`（DPC++）与 Xe 设备 |
| 真实 RTAS 构造 / 硬件兼容性 | ❌ 需具备 Intel Xe 设备 + L0 驱动的环境 |

上游测试的清点数据与逐项不可运行技术原因见 `1.2.3/test_package/MANIFEST.yml` 与 `1.2.3/notes.md`。

## 使用

```bash
conan install --requires=level-zero-gpu-raytracing/1.2.3 -pr=ohos-aarch64
```

依赖：`tbb/2023.0.0.1`、`sse2neon/1.9.1`。
