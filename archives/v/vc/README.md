# vc

## 软件描述
Vc 是一个自由、可移植、快速且简洁的 C++ SIMD 矢量类库（header-only），提供类似 `std::vector` 的 SIMD 类型接口，支持 SSE/AVX 等指令集，未启用时自动回退 Scalar 实现。

## 功能概述
- **SIMD 矢量类型**：`Vc::int_v`、`Vc::float_v`、`Vc::double_v` 等定长矢量
- **SIMD 数组**：`Vc::SimdArray` 动态 SIMD 数组
- **内存分配器**：`Vc::Allocator` 对齐内存分配
- **算法支持**：`Vc::algorithm` SIMD 算法（gather/deinterleave 等）

## OHOS 适配

### 构建方式
- **header-only**：无库编译——`package()` 拷贝 `Vc/` 头文件目录到 include
- CMake 构建（`BUILD_TESTING=OFF` 打包；测试单独 `BUILD_TESTING=ON` 构建）

### 关键攻坚点
1. **aarch64 OHOS 走 Scalar**：`-DVc_IMPL=Scalar`——无 SSE/AVX 指令集时自动回退，全平台可编译
2. **config.h 生成**：CMake 生成的 `Vc/config.h` 需一并打包（含平台宏）
3. **上游测试实测**：`BUILD_TESTING=ON` 构建 tests（unittest 框架）+ ctest 运行，回填真实通过率（rule 4）

### 与 Linux 的差异
- Scalar 实现（无硬件 SIMD 加速）——功能等价，性能为标量

## 依赖关系
无外部依赖（header-only）。

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.4.5 | built | 2026-08-28 | header-only CMake 适配 |

## 参考资料
- 上游仓库: https://github.com/VcDevel/Vc
- 文档: https://vcdevel.github.io/Vc-1.4.5/
