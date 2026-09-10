# libdrawtext

[libdrawtext](https://github.com/jtsiomb/libdrawtext) — 用于 OpenGL 的
抗锯齿文本渲染库（作者 John Tsiombikas / NuclearPixel），带软件光栅化
后端与 FreeType 字体加载。

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 0.6 | 已适配 OHOS | 见 [0.6/notes.md](0.6/notes.md) |

## 许可证

LGPL-3.0-or-later（详见包内 `licenses/COPYING.LESSER`）。

## OHOS 适配要点（0.6）

- **构建系统**：上游为自定义 `sh configure` + `Makefile.in`（非
  autotools/cmake）。构建适配完全通过 make 变量注入完成（零构建补丁）；
  另有 1 个符号契约 bugfix 补丁
  （`0.6/patches/0001-glyphmap-image-export.patch`，见 [0.6/notes.md](0.6/notes.md)）。
- **GL 后端**：OHOS 无桌面 libGL/libGLU。上游 `src/drawgl.c` 自带
  `#ifndef NO_OPENGL` 官方 stub 分支，配方以 `-DNO_OPENGL` 编译掉 GL
  后端；`drawtext.h` 公共 API 保持完整，`dtx_target_raster()` 软件
  光栅化路径与 FreeType 字体链路全功能可用。
- **依赖**：`freetype/2.14.3`（Conan 包，传递头文件声明）、
  `-lpthread`（上游 `USE_THREADS`）。
- **SONAME**：上游安装 `libdrawtext.so → .so.0 → .so.0.5` 链；打包时
  按 E492 将别名物化为真实文件副本，避免包重定位后悬空。

## 使用

```conan
requires = "libdrawtext/0.6"
```

```cmake
find_package(libdrawtext REQUIRED)
target_link_libraries(app PRIVATE libdrawtext::libdrawtext)
```

渲染走软件光栅化路径（无需 GL 上下文）：

```c
#include <drawtext.h>

unsigned char pixels[H][W][4];
struct dtx_font *fnt = dtx_open_font("/system/fonts/HarmonyOS_Sans.ttf", 32);
dtx_target_raster(&pixels[0][0][0], W, H);   /* 先设 raster 目标 */
dtx_use_font(fnt, 32);
dtx_prepare_range(fnt, 32, 32, 126);
dtx_position(x, y);
dtx_string("hello");
```

注意：`dtx_use_font` 会自动选择默认目标，须先调用 `dtx_target_raster`
再 `dtx_use_font`；no-opengl 构建下 `dtx_target_opengl()` 为上游 stub。
