# clutter-1.26.4-gnome-archive-component-stub（草稿）

## 符号面分析（决定性证据）

```
$ nm -D --undefined-only libclutter-1.0.so | grep -E "cogl_pango_|cairo_gobject_"
U cogl_pango_font_map_new
U cogl_pango_font_map_create_context
U cogl_pango_font_map_set_resolution
U cogl_pango_font_map_clear_glyph_cache
U cogl_pango_font_map_set_use_mipmapping
U cogl_pango_font_map_get_renderer   (+2)
U cairo_gobject_context_get_type
U cairo_gobject_surface_get_type
```

libclutter 对 cogl-pango 组件的实际引用面 = 8 符号；对 cairo-gobject = 2 符号。
而制品仓 cogl/1.22.8 二进制不含 cogl-pango 组件（构建时禁用）、图内 cairo/1.18.4
二进制不含 cairo-gobject 组件（无 libcairo-gobject.so 与 .pc）——clutter 的
CLUTTER_BASE_PC_FILES/CLUTTER_DEPS 硬依赖两者，configure PKG_CHECK_MODULES 直接 fatal。

## stub 分类（三类）

| 类 | 符号 | 上游语义 | stub 实现 |
|---|---|---|---|
| 直传 | cogl_pango_font_map_new / create_context / set_resolution / get_renderer | PangoCairoFontMap 的"假子类"（qdata 挂 CoglContext） | 直传 pango 对应 API（行为等价） |
| 不可达 no-op | cogl_pango_font_map_clear_glyph_cache / set_use_mipmapping / ensure_glyph_cache_for_layout / render_layout | GL 渲染器上预填 glyph 缓存纹理 | no-op（OHOS 无显示服务，渲染路径不可达） |
| GType 注册 | cairo_gobject_context/surface_get_type | CAIRO_GOBJECT_BOILERPLATE 的引用计数 boxed 类型 | 逐行等价（g_boxed_type_register_static，类型名字符串照抄上游） |

## 转发 .pc 形态

```
prefix=stub
Name: cogl-pango
Libs: <src>/cogl-pango-stub.o
Cflags: -I<src>
Requires: cogl-1.0 pangocairo
```

Libs 直接带 stub .o（链接期闭合）；Requires 指向真实组件链；同配方先例有真实
文件时优先转发（cairo 包内若在档则 prefix=/ 重写转发，stub 仅兜底分支）。

## X11/显示后端全禁（同 PR 另一素材）

`--disable-x11-backend --disable-gdk-backend --disable-wayland-backend
--disable-quartz-backend --disable-win32-backend --disable-mir-backend
--disable-cex100-backend --disable-evdev-input --disable-tslib-input
--enable-egl-backend`：OHOS 无显示服务与输入子系统，仅 generic EGL 后端。
EGL 经 cogl 封装（libclutter NEEDED 无 libEGL），egl.h 由 clang 默认 sysroot
解析（裸编译 #include <EGL/egl.h> 验证过），无需直连 egl/gles2 包。

## verify_builds

本 PR（clutter 1.26.4，conan create 全绿 + test_package 17 用例 ALL PASS）。

## fallback

不可行时（符号面远超子集/上游语义无法等价）：改走依赖包重打包线（cogl/cairo
带组件版本入档，cogl/1.22.8.1 重签先例），或在有显示能力的设备上重开渲染路径。
