# libXrandr

X RandR Extension Library - X Resize and Rotate extension library.

## Description

libXrandr provides the X Resize, Rotate and Reflect (RandR) extension library for the X Window System. It allows clients to query and change the screen configuration, including:
- Screen size and resolution
- Screen rotation and reflection
- Monitor hot-plugging support
- Multi-monitor configuration

## Dependencies

- libX11 (>= 1.8.10)
- libXext (>= 1.3.6)
- libXrender (>= 0.9.11)
- randrproto (>= 1.6.0)

## Versions

### 1.5.5 (2026-05-25)

- **Build System**: cmake (规避 HMDFS SELinux 权限限制)
- **Key Features**:
  - 生成动态库 (libXrandr.so) + 静态库 (libXrandr.a)
  - 启用 `-fPIC` (CMAKE_POSITION_INDEPENDENT_CODE ON)
  - 支持 XRandR 1.6 规范
- **Notes**: 使用 cmake 替代 autotools，避开 OpenHarmony HMDFS 文件系统的 hmmac 强制访问控制限制

## Installation

```bash
# pkg-config 验证
pkg-config --modversion xrandr  # 1.5.5
pkg-config --libs xrandr        # -L${libdir} -lXrandr

# 头文件
#include <X11/extensions/Xrandr.h>
```

## License

MIT License

## Source

https://www.x.org/releases/individual/lib/libXrandr-1.5.5.tar.gz