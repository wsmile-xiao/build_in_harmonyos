# half

`half` 是 IEEE 754 半精度（binary16）浮点 **C++ 库**（原作者 Christian Rau，
现由 [ROCm/half](https://github.com/ROCm/half) 维护）。整个库是**单个自包含头文件**
`include/half.hpp`，无需编译。

## 功能概述

- `half` 类型：从 `float`/`double`/`int` 构造与转换（`half_cast` 支持显式舍入模式）
- 完整的算术/比较运算符重载
- 分类函数（`fpclassify`/`isfinite`/`isinf`/`isnan`/`isnormal`/`signbit`）
- 数学函数（三角/双曲/指数/幂/取整等，以单精度实现）
- `std::numeric_limits<half>` 特化、哈希支持、C++11 用户字面量

## OHOS 适配

- **header-only**：`package_type = "header-library"`，`package()` 仅安装
  `include/half.hpp` → `include/half/half.hpp`（与上游 CMake 安装路径一致）及
  `LICENSE.txt`。下游 `#include <half/half.hpp>`。
- **不使用上游 CMakeLists.txt**：其 `find_package(ROCM REQUIRED)` 与
  `rocm_setup_version()`/`rocm_create_package()` 来自独立的 `rocm-cmake` 包，该包
  未发布到 ohpcd 制品仓；且 half 无需编译。按 PF4/R36 不得声明不可解依赖，故配方
  自包含。
- **版本口径**：包版本跟随 ROCm 发布列车（如 `7.2.4`）；`half.hpp` 头部自报版本为
  `1.12.0`（上游 header 版本）。
- **已知平台差异**：上游 `test11` 套件以 `std::<func>(double)` 为参考，而 half 的
  数学函数以单精度实现，`atan2/hypot/asinh/acosh/lgamma` 在平台上出现 1 half-ULP
  参考差异（上游 README 已声明单精度实现）。不影响库的转换/算术正确性。

## 依赖关系

- 编译依赖：无
- 运行依赖：无（纯头文件）

## 参考资料

- 上游仓库：https://github.com/ROCm/half
- 源码（7.2.4）：https://github.com/ROCm/half/archive/refs/tags/rocm-7.2.4.tar.gz
