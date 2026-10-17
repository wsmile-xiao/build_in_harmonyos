# units-cpp（units）

> 编译期、header-only 的 C++14 单位换算与量纲分析库，零依赖。

## 简介

units 用模板与 `std::ratio` 在编译期表达物理量及其量纲，提供长度、质量、时间、温度、
能量、功率、速度、数据等大量预定义单位，并支持用户自定义单位、复合单位与用户定义字面量：

```cpp
#include <units.h>
using namespace units::length;
using namespace units::literals;

meter_t distance = 2.5_km;                       // 参数化字面量
double feet = distance.convert<foot_t>().to<double>();
auto speed = distance / time::second_t(10);      // 复合单位 m/s
```

## OHOS 适配要点

- header-only：包内只安装 `include/units.h`，无 `.a`/`.so`，被引用为 `#include <units.h>`。
- **CMake 4.x**：上游声明 `cmake_minimum_required(VERSION 3.2...3.5)`，需设置
  `CMAKE_POLICY_VERSION_MINIMUM=3.5` 才能配置。
- **上游测试真实运行**：GoogleTest 1.12.1 以本地 zip 随源码分发，`build()` 中编译并运行
  188 个 `TEST_F`（实测注册数）；其中 2 项因平台环境差异排除：
  `UnitContainer.to_string_locale`（OHOS bionic 不提供 `de_DE.utf8`/`en_US.utf8` locale 数据）
  与 `UnitContainer.cout`（gtest `CaptureStdout` 硬编码写入只读的 `/tmp`），其余 186/188 通过。
- **消费者验证**：`test_package` 通过 `find_package(units)` + `units::units` 使用安装后的
  包，共 20 项检查（含换算、字面量、仿射温度、数据单位、`to_string`、`unit_cast`、chrono 互操作）。
- CMake 目标：`units::units`。

## 依赖

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| （无） | - | 仅 C++ 标准库（C++14） |

## 参考

- [源码仓库](https://github.com/nholthaus/units)
- [上游 README](https://github.com/nholthaus/units/blob/master/README.md)
