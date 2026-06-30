# gtk 4.22.4 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-30
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# 前置：重新编译harfbuzz启用glib支持（hb-glib.h缺失）
# 见harfbuzz子任务归档

# meson配置（Broadway backend，禁用X11/Wayland/Vulkan等不支持特性）
meson setup builddir --prefix=$DEFAULT_PREFIX \
  -Dwayland-backend=false -Dx11-backend=false \
  -Dbroadway-backend=true -Dvulkan=disabled \
  -Dmedia-gstreamer=disabled -Dprint-cups=disabled \
  -Dprint-cpdb=disabled -Dintrospection=disabled \
  -Dbuild-tests=false -Dbuild-testsuite=false \
  -Dbuild-demos=false -Dbuild-examples=false \
  -Dman-pages=false -Ddocumentation=false \
  -Dcolord=disabled -Dtracker=disabled \
  -Dsysprof=disabled -Dcloudproviders=disabled \
  -Daccesskit=disabled -Df16c=disabled \
  -Dscreenshots=false

# 编译
ninja -C builddir -j2

# staging安装
DESTDIR=$TEST_PREFIX ninja -C builddir install

# 本地安装验证
ninja -C builddir install
pkg-config --modversion gtk4  # → 4.22.4
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `epoxy/egl.h` file not found in gdkdmabuf.c | HAVE_DMABUF被定义但EGL不可用，gdkdmabuf.c无条件包含epoxy/egl.h | 在`#include <epoxy/egl.h>`处添加`#ifdef HAVE_EGL`守卫 |
| 2 | `hb-glib.h` file not found | harfbuzz编译时未启用glib集成，缺少hb-glib.h头文件 | 重新编译harfbuzz启用glib支持(-Dglib=enabled) |
| 3 | `-lepoxy` library not found during linking | libepoxy.so缺少.so符号链接 | 创建libepoxy.so → libepoxy.so.0 → libepoxy.so.0.0.0符号链接 |

## 源码修改

| 文件 | 补丁 | 说明 |
|------|------|------|
| gdk/gdkdmabuf.c | 0001-gdk-gdkdmabuf.c.patch | 为epoxy/egl.h include添加HAVE_EGL守卫 |

## 依赖版本

- glib-2.0: 2.88.0
- pango: (系统)
- cairo: (系统)
- harfbuzz: 14.2.0 (含glib集成)
- gdk-pixbuf-2.0: (系统)
- graphene-1.0: (系统)
- fribidi: (系统)
- epoxy: 1.5.10
- libepoxy: 1.5.10

## 验证结果

```bash
pkg-config --modversion gtk4
# 4.22.4
pkg-config --libs gtk4
# -L/storage/Users/currentUser/usr/local/lib -lgtk-4 -lpangocairo-1.0 -lpango-1.0 -lharfbuzz ...
```

## meson配置选项

- Display backends: broadway (HTML5/Web)
- Print backends: file
- Media backends: (none)
- Vulkan: disabled
- Introspection: disabled
- Documentation: disabled

## 注意事项

1. GTK4在OHOS上使用Broadway backend（HTML5/Web渲染），无X11/Wayland支持
2. harfbuzz必须启用glib集成才能编译GTK4
3. libepoxy需要确保符号链接存在
---

**编译结束**: 2026-05-30 20:24
**最终状态**: built
