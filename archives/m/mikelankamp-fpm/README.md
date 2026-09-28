# mikelankamp-fpm（fpm）

`fpm`（fixed-point math）是一个 C++ **header-only 定点数学库**，目标是作为浮点类型的
drop-in 替身：用整数实现 `<cmath>` 风格的数学函数，适用于没有 FPU / 浮点较慢、或需要
确定性数值结果的场景。

## 功能概述

- 三种定点类型：`fpm::fixed_16_16`、`fpm::fixed_24_8`、`fpm::fixed_8_24`
  （由 `template <Base, Intermediate, FractionBits>` 的 `fpm::fixed` 实例化）。
- 覆盖 `<math.h>` 常用函数：`sqrt`/`cbrt`/`pow`/`exp*`/`log*`/`sin`/`cos`/`tan`/`asin`/
  `acos`/`atan`/`atan2`/`ceil`/`floor`/`round`/`fmod`/`remainder`/`hypot`/`fabs` 等
  （`<fpm/math.hpp>`）。
- 流插入/提取：`operator<<` / `operator>>`（`<fpm/ios.hpp>`），格式化语义对齐
  `std::num_get`/`std::num_put`。
- 类型特性与分类：`fpm::is_fixed`、`fpclassify`/`isfinite`/`isinf`/`isnan`/`signbit`
  等；`std::hash<fpm::fixed<...>>` 特化。
- 显式构造：整数/浮点到定点是 `explicit`，杜绝隐式转换带来的精度事故。

## OHOS 适配要点

- **打包形态**：header-only。conan 包内只有 `include/fpm/{fixed,ios,math}.hpp` 与
  `licenses/LICENSE`，`package_id` 清空为单一 id；无 `bin/`、无 `lib/`，因此
  **不声明 `commands.json`**。
- **构建系统**：上游 CMake。v1.1.0 的 `CMakeLists.txt` **没有任何 option 开关**，且
  默认 `all` 目标包含两个 `ExternalProject_Add`（libfixmath、cnl，均需 git clone）以及
  benchmark/accuracy 两个工具。配方 `build()` 因此只按目标构建 `fpm-test`
  （`cmake.build(target="fpm-test")`），既不联网、也不编译与交付物无关的工具。
- **依赖**：0 外部依赖。测试框架是上游随包内嵌的 `3rdparty/googletest`。
- **补丁**：本版本 **无需任何补丁**，`patches/` 不存在；上游测试用例数与断言数零改动。
- **上游测试**：设备端实跑 `fpm-test` 与 `ctest` 两条路径均全绿，计数与四个候选口径见
  `1.1.0/test_package/MANIFEST.yml`（N = 34671，候选数法最大值）。
- **已知的上游精度事实**（非 OHOS 差异）：上游 minimax 多项式在 `fixed_16_16` 下
  `cos(0)` 与 `sin(pi/2)` 返回 65535/65536，即比 1 低 1 LSB（1/65536 ≈ 1.53e-5）。
  本仓库未做任何修改，`test_package` 按 1 LSB 容差断言并写明依据。

## 依赖关系

- 编译依赖：无（只需 C++11 或更高的标准库）。
- 运行依赖：无。

## 参考资料

- 源码仓库：<https://github.com/MikeLankamp/fpm>
- 上游 tag：`v1.1.0`（源码 tarball 的 sha256 见 `1.1.0/conandata.yml`）
