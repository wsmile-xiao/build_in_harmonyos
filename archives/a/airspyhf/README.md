# AirSpy HF+

AirSpy HF+ 用户态驱动（libairspyhf）及配套命令行工具，用于软件定义无线电（SDR）。
提供 libairspyhf 共享/静态库和 airspyhf_lib_version、airspyhf_info、airspyhf_rx、
airspyhf_gpio、airspyhf_calibrate 等工具。

## 功能概述

- **libairspyhf**: AirSpy HF+ SDR 设备的用户态 USB 驱动库（依赖 libusb-1.0）
- **airspyhf_lib_version**: 打印库版本（调用 `airspyhf_lib_version()` API）
- **airspyhf_info**: 查询设备信息和库版本
- **airspyhf_rx**: 接收 IQ 采样数据
- **airspyhf_gpio**: 读写板载 GPIO
- **airspyhf_calibrate**: 读取/写入校准值

## 来源

- 源码仓库: https://github.com/airspy/airspyhf
- 版本标签: 1.6.8

## 许可证

BSD-3-Clause（顶层 LICENSE 为 BSD 3-Clause）

## OHOS 适配

### 关键适配点

1. **CMake UNIX 变量问题**: CMake 不识别 HarmonyOS 平台（E092），
   `if( ${UNIX} )` 不成立导致 lib/ 与 include/ 安装目标被跳过。
   配方 `generate()` 设 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64` 解决。

2. **CMake 版本兼容**: 上游 `cmake_minimum_required(2.8)`，需设
   `CMAKE_POLICY_VERSION_MINIMUM=3.5` 兼容 CMake 4.x（同 Homebrew PR #54）。

3. **FindUSB1 依赖解析**: 上游 `FindUSB1.cmake` 使用 `LIBUSB_INCLUDE_DIR`/
   `LIBUSB_LIBRARIES` cache 变量，配方从 libusb/1.0.27 Conan 依赖包显式解析。

4. **ELF 签名**: 鸿蒙要求 .so 与可执行文件 ELF 签名后方可加载执行，
   配方 `package()` 统一签名（`binary-sign-tool`, SHA256withECDSA）。

5. **头文件路径**: 上游安装到 `include/libairspyhf/`，`package_info()` 的
   `includedirs` 指向该子目录使 `#include <airspyhf.h>` 可解析。

## 依赖关系

### 编译依赖
- **libusb/1.0.27**: Conan ohpcd 制品仓（已发布）

### 运行依赖
- **pthread**: 系统内置
- **libusb-1.0**: 运行时 USB 设备访问（Conan 依赖链自动拉取）

## 参考资料

- 官方仓库: https://github.com/airspy/airspyhf
- AirSpy 官网: https://airspy.com

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [1.6.8](./1.6.8/) | published | 2026-08-07 |
