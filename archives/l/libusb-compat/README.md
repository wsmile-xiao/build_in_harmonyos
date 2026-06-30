# libusb-compat

**描述**: libusb-compat 是一个兼容层库，提供 libusb 0.1 API，底层使用 libusb-1.0。

**主页**: https://libusb.info/

**许可证**: LGPL-2.1

**分类**: library

## 版本

### 0.1.7 (2026-05-26)
- **状态**: built
- **构建系统**: cmake
- **依赖**: libusb-1.0 (1.0.27)

## 说明

libusb-compat 允许使用旧版 libusb 0.1 API 的应用程序无缝迁移到 libusb-1.0。它提供了完整的 libusb 0.1 API 兼容性，但底层实现使用现代的 libusb-1.0 库。

### 编译说明

由于 HMDFS 文件系统的 hmmac 强制访问控制，此软件使用 cmake 编译而非 autotools。源码本身只提供 autotools 构建系统，因此需要创建自定义的 CMakeLists.txt。