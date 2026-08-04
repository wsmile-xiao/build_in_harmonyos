# gdk-pixbuf

gdk-pixbuf 是 GTK 生态使用的图像加载与像素缓冲区处理库，支持 PNG、JPEG、GIF、TIFF 等格式。

**官网**: https://gitlab.gnome.org/GNOME/gdk-pixbuf

**分类**: graphics/library

## 版本列表

- 2.42.12 (2026-05-19) - built
- 2.44.6 (2026-07-31) - Conan 配方迁移，双真机验证通过

## 依赖

- glib >= 2.56
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
  -Dpng=enabled -Djpeg=enabled -Dtiff=enabled -Dgif=enabled \
  -Dbuiltin_loaders=all -Dtests=true \
  -Dman=false
```

## 注意事项

1. 需要禁用 gio_sniffing 以避免 shared-mime-info 依赖
2. PNG、JPEG、TIFF、GIF 加载器均显式启用并内置，避免不可重定位的加载器缓存
3. 上游 23 个 Meson 测试在鸿蒙原生构建时执行；两台 HarmonyOS PC 均为 23/23 通过
4. man pages 需要 rst2man，配方中禁用
