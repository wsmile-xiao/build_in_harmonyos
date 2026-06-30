# drawing - 简易图像编辑器

## 软件简介

drawing 是一个类似 Microsoft Paint 的简易图像编辑器，面向 GNOME 桌面环境。支持 PNG、JPEG 和 BMP 格式。

**主要功能**:
- 画笔、铅笔、橡皮擦等绘图工具
- 直线、弧线、形状绘制
- 文本标注
- 图像裁剪、缩放、旋转
- 颜色拾取与调整
- 滤镜效果（模糊、饱和度、透明度等）

## 已编译版本

| 版本 | 状态 | 构建系统 | 补丁数 | 日期 |
|------|------|----------|--------|------|
| 1.0.2 | ✅ success | meson | 2 | 2026-05-30 |

## 快速安装

```bash
# 下载预编译包
tar xzf drawing-1.0.2-ohos-aarch64.tar.gz -C ~/usr/local

# 运行安装脚本
cd ~/usr/local/drawing-1.0.2-ohos-aarch64
sh install-drawing-1.0.2.sh
```

## 编译指导

### 构建系统说明

本软件使用 Meson 构建，需要 GTK+3 和相关 GNOME 组件。

```bash
# Meson 构建（禁用翻译和帮助文档）
meson setup builddir -Denable-translations-and-appdata=false -Duse-uuid-as-binary-name=false
meson compile -C builddir -j$(nproc)
DESTDIR=$TEST_PREFIX meson install -C builddir
```

### 补丁应用

需要应用以下补丁以支持 HarmonyOS:

1. **0001-skip-help-subdir.patch**: 跳过 help 子目录（itstool 需要 libxml2 Python 模块，OHOS 上不可用）
2. **0002-skip-update-desktop-database.patch**: 在 postinstall 脚本中跳过 update-desktop-database（OHOS 上不可用）

## 已知限制

- help 文档无法编译（itstool 依赖不可用）
- update-desktop-database 在 OHOS 上不可用，安装脚本跳过此步骤

## 依赖关系

- **运行依赖**: GTK+3, glib, gdk-pixbuf, cairo, pango, harfbuzz, freetype, fontconfig
- **编译依赖**: meson, ninja, GTK+3-dev, glib-dev

## 参考资料

- 官方网站: https://maoschanz.github.io/drawing/
- 源码仓库: https://github.com/maoschanz/drawing