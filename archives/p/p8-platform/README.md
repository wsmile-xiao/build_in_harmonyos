# p8-platform

P8 Platform 是 Pulse-Eight 项目的平台支持库，提供跨平台的操作系统抽象层。

## 功能概述

- **线程支持**：跨平台线程创建和管理
- **Socket 抽象**：网络通信抽象层
- **文件系统操作**：跨平台文件操作
- **时间管理**：时间和定时器抽象
- **进程管理**：进程创建和管理

## OHOS 适配

### 适配要点

1. **CMake 构建系统**：自动识别 HarmonyOS 平台，无需特殊配置
2. **静态库编译**：编译为静态库（libp8-platform.a），无运行时依赖
3. **Thread 支持**：需要系统的 pthread 库支持

### 已知问题

- 无已知问题

### 与 Linux 的差异

- HarmonyOS 使用 musl libc，与 Linux glibc 兼容性良好
- 所有 POSIX API 均可正常使用

## 依赖关系

### 编译依赖

- CMake 3.12.0+
- C++11 编译器（clang/clang++）
- Threads（pthread）

### 运行依赖

- 无运行时依赖（静态库）

## 参考资料

- 官方仓库：https://github.com/Pulse-Eight/platform
- 相关项目：Pulse-Eight 的其他项目（如 libcec）