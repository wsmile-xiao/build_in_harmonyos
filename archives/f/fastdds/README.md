# Fast DDS

## 软件简介

Fast DDS（前身为 FastRTPS）是 eProsima 开发的开源 DDS（Data Distribution Service）实现，是针对嵌入式系统的最完整的开源 DDS 中间件。它实现了 DDS DCPS（数据分发服务发布-订阅层）和 DDS RTPS（实时发布订阅有线协议）规范，提供高性能的发布-订阅通信机制。

## 功能概述

- **RTPS 协议实现**：完整实现 DDS RTPS 有线协议，确保不同 DDS 实现之间的互操作性
- **发布-订阅模型**：支持发布者和订阅者之间的数据分发
- **QoS 策略**：支持丰富的服务质量策略（可靠性、持久性、历史深度等）
- **安全机制**：支持基于 SSL/TLS 的身份验证、访问控制和数据加密
- **Discovery 机制**：自动发现网络中的参与者，支持简单和复杂的发现协议
- **Transport 层**：支持 UDP、TCP、SHM（共享内存）等多种传输方式
- **C++ API**：提供完整的 C++ 编程接口

## OHOS 适配要点

- **平台检测**：CMake 不识别 HarmonyOS 平台，会出现 "System is unknown to cmake" 警告，需要创建 `Platform/HarmonyOS` 配置文件或设置 `CMAKE_SYSTEM_NAME`
- **子模块依赖**：Fast-DDS 使用 Git 子模块管理 asio 和 tinyxml2，在非 Git 环境中需手动下载填充 `thirdparty/` 目录
- **依赖预编译**：Fast-CDR 和 foonathan_memory 需要预先编译安装，CMake 通过 `find_package` 查找
- **库名称**：v2.1.0 使用旧名称 `fastrtps`，生成的库文件为 `libfastrtps.so`
- **C++ 标准**：需要 C++14 编译器支持
- **编译器**：在 OHOS 平台上使用 Clang 编译器

## 依赖关系

### 编译依赖
| 依赖 | 版本 | 说明 |
|------|------|------|
| Fast-CDR | 1.0.16 | eProsima CDR 序列化库，必须预编译安装 |
| asio | 1.18.0+ | 头文件库，异步 I/O 框架 |
| tinyxml2 | 8.0.0+ | XML 解析库 |
| foonathan_memory | 0.6-2 | 内存分配器，通过 foonathan_memory_vendor 安装 |
| CMake | 3.5+ | 构建系统 |

### 可选依赖
| 依赖 | 说明 |
|------|------|
| OpenSSL | TLS/SSL 安全支持（可选） |

## 参考资料

- 官方网站：https://www.eprosima.com/
- 源码仓库：https://github.com/eProsima/Fast-DDS
- 文档：https://fast-dds.docs.eprosima.com/
- DDS 规范：https://www.omg.org/spec/DDS/
- ConanCenter 配方：https://github.com/conan-io/conan-center-index/tree/master/recipes/fast-dds
