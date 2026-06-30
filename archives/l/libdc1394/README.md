# libdc1394

IEEE 1394 (FireWire) 数字摄像头控制库。

## 简介

libdc1394 是一个用于控制 IEEE 1394 (FireWire/i.LINK) 数字摄像头的 C 语言库。它提供了完整的 API 来发现、配置和从 FireWire 摄像头捕获图像，支持 IIDC (Industrial and Instrumentation Digital Camera) 标准协议。

## 主要功能

- **设备发现**: 自动枚举系统中的 FireWire 摄像头
- **图像捕获**: 支持 DMA 和非 DMA 模式捕获
- **视频模式**: 支持 Format_0/1/2/7 等多种视频格式
- **相机控制**: 白平衡、增益、快门、帧速率等参数调节
- **Format7**: 支持 Format7 区域感兴趣 (ROI) 配置
- **颜色转换**: YUV/RGB/MONO 格式互转
- **厂商扩展**: AVT、Basler、Pixelink 等厂商特有功能

## 鸿蒙平台适配说明

### 编译信息

- **版本**: 2.2.7
- **构建系统**: autotools
- **编译器**: clang 15.0.4
- **依赖**: libraw1394 (预编译包)
- **状态**: published (2026-06-02)

### 平台适配要点

1. config.guess/config.sub 需添加 ohos 检测 (E007/E072)
2. clang 不支持 GCC VLA-in-struct 扩展，需改为固定大小数组
3. HMDFS 上 config.status 的 mktemp/umask 组合需特殊处理
4. libtool 版本需与系统版本匹配 (2.4.7)
5. configure 中 AM_PATH_SDL 宏为上游已知问题

### 硬件限制

**IEEE 1394 硬件依赖**: 本库的核心功能（相机发现、图像捕获、总线控制等）需要实际 FireWire 硬件。在无 FireWire 设备的鸿蒙平台上：
- `dc1394_new()` 返回 NULL（无法初始化后端）
- `dc1394_camera_enumerate()` 无法发现设备
- 命令行工具 `dc1394_reset_bus` 报错退出

这是硬件依赖的预期行为，不影响库作为依赖项被其他软件链接使用。库的符号导出、pkg-config、编译链接均正常工作。

### 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libdc1394.so.26.0.1 | 230KB | 共享库 (ELF 64-bit arm64) |
| libdc1394.a | 356KB | 静态库 |
| dc1394_reset_bus | 22KB | 命令行工具 |
| dc1394/*.h | 12个 | 头文件 |
| libdc1394-2.pc | 248B | pkg-config |