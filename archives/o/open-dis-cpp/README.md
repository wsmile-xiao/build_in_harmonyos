# open-dis-cpp

`open-dis-cpp` 是分布式交互仿真协议 **DIS（Distributed Interactive Simulation，IEEE 1278.1）** 的 C++ 实现，
把 DIS 报文（PDU）序列化/反序列化成 C++ 类，供仿真、训练、可视化类应用通过 UDP 等传输层收发使用。
代码主体由 `xmlpg` 代码生成器从 DIS 标准描述生成。

## 功能概述

- **DIS6（IEEE 1278.1a-1998）协议库**：`libOpenDIS6`，提供 140+ 个 PDU 类（EntityStatePdu、DetonationPdu、
  CollisionPdu 等）与 `DIS::DataStream` 字节流编解码。
- **DIS7（IEEE 1278.1-2012）协议库**：`libOpenDIS7`，新一代 PDU 集合（含 DirectedEnergy、LiveEntity 等），
  与 DIS6 类同名但内存布局不同。
- **字节序处理**：`DIS::DataStream` 按调用方给定的 `DIS::Endian`（DIS 协议默认大端/网络序）读写，
  与宿主字节序解耦。
- **CMake 安装导出**：安装 `OpenDISConfig.cmake` 与 `OpenDIS::OpenDIS6/OpenDIS7` 目标，供 `find_package(OpenDIS)` 使用。

## OHOS 适配要点

- **零外部依赖**：库与测试只用标准 C++（`cstdlib/cstring/iostream/map/ostream/string/vector`）+ 自身头文件，
  W0 双源复核（CMake `find_package` 面 + 源码 `#include` 面）均无第三方依赖。
- **CMake 4.x 兼容**：上游 `cmake_minimum_required(VERSION 3.2)`，CMake 4.1 已移除 `<3.5` 兼容，
  必须给 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（设备与 CI 同为 CMake 4.1.2）。
- **两库不可混链**：DIS6/DIS7 大量同名类位于同一 `namespace DIS`（92 个同名头文件），同链会互相占位（ODR 风险），
  Conan 配方拆成 `dis6` / `dis7` 两个 component，消费者按协议版本二选一。
- **可选依赖 SDL2/SDL2_net**：仅 `BUILD_EXAMPLES=ON` 的示例程序需要，缺省关闭即不构成依赖。
- **上游测试**：自带 Catch2 v2.13.10（`test/catch.hpp` 单头），`BUILD_TESTS=ON` 后由 CTest 驱动 8 个 `TEST_CASE`。

## 依赖关系

- 编译依赖：无（C++11 标准库 + CMake ≥ 3.2，实际以 CMake 4.x + clang 15 验证）
- 运行依赖：无（动态链接时仅需 libc/libc++）

## 参考资料

- 上游仓库：https://github.com/open-dis/open-dis-cpp
- DIS 标准：IEEE 1278.1（DIS6）、IEEE 1278.1-2012（DIS7）
- 代码生成器：https://github.com/open-dis/xmlpg
