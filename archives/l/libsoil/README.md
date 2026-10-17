# libsoil

**SOIL — Simple OpenGL Image Library**（纯 C 图像加载/保存库）

libsoil 提供轻量级的图像解码/编码 API：从内存/文件加载 BMP、PNG、TGA、DDS，
并支持保存 BMP/TGA。上游同时包含 OpenGL 纹理上传 API（`SOIL_load_OGL_texture` 等），
在 HarmonyOS PC 上无 OpenGL 运行时/头文件，已通过 `SOIL_NO_GL` 特性宏编译掉 GL 依赖，
保留纯图像 API（SOIL_load_image / SOIL_load_image_from_memory / SOIL_save_image /
SOIL_free_image_data / SOIL_last_result）。

## 用法

```c
#include "SOIL.h"

int w, h, channels;
unsigned char *img = SOIL_load_image("photo.png", &w, &h, &channels, SOIL_LOAD_RGBA);
// ... 使用 img ...
SOIL_free_image_data(img);
```

| API | 说明 |
|-----|------|
| `SOIL_load_image` / `SOIL_load_image_from_memory` | 解码 BMP/PNG/TGA/DDS 到内存 |
| `SOIL_save_image` / `SOIL_save_image_from_memory` | 保存 BMP/TGA |
| `SOIL_last_result` | 最近一次调用的错误信息 |
| `SOIL_LOAD_RGB/RGBA` | 强制通道数（RGB/RGBA）转换 |

## 构建

- 构建系统：上游纯 Makefile（`projects/makefile/makefile`，无 configure/CMake）
- 版本：1.07.20080707.dfsg（Debian 官方镜像源，`.dfsg` 为去非自由组件标记）
- 许可证：MIT
- 源码：https://deb.debian.org/debian/pool/main/libs/libsoil/libsoil_1.07.20080707.dfsg.orig.tar.gz

## OHOS 适配

- `SOIL_NO_GL` 特性宏编译掉 GL 依赖函数（`patches/0001-src-SOIL.c.patch`）
- makefile 默认 `CXX=gcc` 且 `-s strip` → 覆盖为 `CXX=clang CXXFLAGS="-O2 -Wall -DSOIL_NO_GL"`
- 构建前需 `mkdir -p obj`（makefile 假定 obj/ 已存在）
- 上游测试 `src/test_SOIL.cpp` 为 Windows-only GUI 程序，不可移植到 OHOS；
  test_package 提供实质功能测试（四格式解码 + 保存往返 + 平台断言）
