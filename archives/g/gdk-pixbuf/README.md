# gdk-pixbuf

**描述**: GTK+ 图像加载库，支持多种图像格式（PNG、JPEG、GIF、TIFF等）

**官网**: https://gitlab.gnome.org/GNOME/gdk-pixbuf

**分类**: graphics/library

## 版本列表

- 2.42.12 (2026-05-19) - built

## 依赖

- glib >= 2.0
- libpng
- libjpeg-turbo
- libtiff（可选）
- meson >= 0.50
- ninja

## 编译说明

gdk-pixbuf 使用 meson 构建系统。推荐配置选项：

```bash
meson setup build --prefix=$DEFAULT_PREFIX \
  -Dgio_sniffing=false \
  -Dtiff=disabled \
  -Dtests=false \
  -Dman=false
```

## 注意事项

1. 需要禁用 gio_sniffing 以避免 shared-mime-info 依赖
2. libtiff 可选，未安装时禁用 tiff loader
3. man pages 需要 rst2man，建议禁用