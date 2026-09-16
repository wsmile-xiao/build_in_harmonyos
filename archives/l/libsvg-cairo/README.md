# libsvg-cairo

libsvg-cairo is the cairo rendering backend for libsvg: it parses SVG
documents through libsvg and draws them onto cairo surfaces. Part of the
cairographics snapshot ecosystem (2005 era).

> 注意：libsvg / libsvg-cairo 与 librsvg 是不同的库，互不相关。

## 已编译版本

- 0.1.6 (2026-09-03) — OpenHarmony / HarmonyOS PC aarch64

## 依赖

- libsvg/0.1.4（SVG 解析）
- cairo/1.18.4（2D 渲染；本库仅使用其核心公共 API，全部在 1.18 中存在）
- libsvg 的传递依赖（libxml2/libpng/libjpeg/zlib）由 Conan 依赖图解析

## 构建系统

- autotools（上游 configure + make 原样保留）
- OHOS 适配补丁 2 个（config.guess/config.sub 识别 ohos；configure
  mktemp 探针 umask），均为 portability，不改上游源码

## 特性

- `svg_cairo_parse*` 解析 SVG（文件/缓冲/分块）
- `svg_cairo_render` 渲染到任意 cairo surface（含 headless image surface）
- `svg_cairo_get_size` 查询文档尺寸
- 无 CLI 工具，无 X11 运行时依赖（`--without-x`）

## 使用方法

```cmake
find_package(libsvg-cairo CONFIG REQUIRED)
# svg-cairo.h includes svg.h and cairo.h directly, so consumers also
# need the headers of both public dependencies (same pattern as the
# cairomm/1.16.2 test_package in this repo):
find_package(libsvg CONFIG REQUIRED)
find_package(cairo CONFIG REQUIRED)
target_link_libraries(my_app PRIVATE
    libsvg-cairo::libsvg-cairo
    libsvg::libsvg
    cairo::cairo)
```

```c
#include <svg-cairo.h>

svg_cairo_t *svgc;
svg_cairo_create(&svgc);
svg_cairo_parse_buffer(svgc, svg_text, strlen(svg_text));
svg_cairo_render(svgc, cr);   /* any cairo_t, e.g. image surface */
svg_cairo_destroy(svgc);
```

## 上游

- 主页: https://cairographics.org/
- 源码: https://cairographics.org/snapshots/libsvg-cairo-0.1.6.tar.gz
- 许可证: LGPL-2.0-or-later
