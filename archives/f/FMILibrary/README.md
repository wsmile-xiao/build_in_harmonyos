# FMILibrary

## 软件描述

FMILibrary (FMI Library) 是一个开源的 C 库，实现了 FMI (Functional Mock-up Interface) 标准，用于导入和操作 FMU (Functional Mock-up Units)。FMU 是一种标准化的模型交换格式，广泛用于工程仿真领域。

## 主要功能

- **FMU 导入**: 支持解压和加载 FMU 文件
- **FMI 标准**: 支持 FMI 1.0, 2.0 和 3.0 三个版本
- **XML 解析**: 解析 FMU 内的 modelDescription.xml
- **C API**: 提供完整的 C 接口用于模型实例化和仿真
- **共享库加载**: 劯态加载 FMU 内的二进制文件
- **内置依赖**: 自带 zlib, expat, minizip, catch2 第三方库

## 应用场景

- 模型交换和协同仿真
- 嵌入式系统仿真
- 汽车工业 (AUTOSAR)
- 工业自动化
- 控制系统开发

## 编译版本

| 版本 | 状态 | 平台 | 编译器 | 测试结果 |
|------|------|------|--------|---------|
| 2.0.3 | published | OpenHarmony (aarch64) | clang 15.0.4 | 20/26 passed (77%) |

## 官方信息

- **源码仓库**: https://github.com/modelon-community/fmi-library
- **许可证**: BSD-3-Clause
- **FMI 标准**: https://fmi-standard.org/
