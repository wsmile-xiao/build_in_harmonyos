# libindi

**Display**: INDI (Instrument Neutral Distributed Interface)

**Description**: INDI 是一套用于天文仪器控制的开源协议和库，支持望远镜、相机、聚焦器等设备的网络化控制。libindi 提供了服务器和客户端库，使得天文软件能够统一控制各种设备。

## 核心组件

- **indiserver**: INDI 服务器，管理设备驱动程序和客户端连接
- **libindiclient**: INDI 客户端静态库，用于开发 INDI 客户端应用

## OHOS 适配要点

1. **构建系统**: 使用 CMake，需设置 `-DCMAKE_SYSTEM_NAME=Linux` 以绕过平台检测（E092）
2. **syscall 替换**:
   - `stime()` → `clock_settime()`（stime syscall 不可用）
   - `mremap()` → `munmap()+mmap()`（mremap syscall 不支持）
3. **依赖**: cfitsio, nova, libusb1, curl, gsl, jpeg, zlib

## 常见依赖

- cfitsio: FITS 文件处理库
- nova: 天文计算库
- libusb1: USB 设备访问
- curl: HTTP 客户端
- gsl: GNU Scientific Library
- jpeg: JPEG 图像处理
- zlib: 压缩库

## Homepage

https://indilib.org

## License

LGPL-2.1+

## Category

astronomy