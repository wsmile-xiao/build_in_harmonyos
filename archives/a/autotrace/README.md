# autotrace

Bitmap to vector graphics converter - 将位图图像转换为矢量图形。

## 软件简介

autotrace 是一个将位图图像（BMP、TGA、PNM 等）转换为矢量图形（SVG、EPS、DXF 等）的工具。它通过分析图像中的轮廓和颜色边界，生成可缩放的矢量路径。

## 主要功能

- 支持输入格式：BMP、TGA、PBM、PGM、PPM（当前编译禁用了 ImageMagick/PNG 支持）
- 支持输出格式：SVG、EPS、DXF、EMF、PDF、FIG、SK、POV 等
- 轮廓追踪算法：基于像素边缘检测
- 曲线拟合：将轮廓转换为平滑的贝塞尔曲线

## OHOS 适配要点

### 构建依赖

- **必需**：glib 2.0、pkg-config、gettext、intltool
- **可选**（当前禁用）：ImageMagick、GraphicsMagick、libpng、pstoedit

### Bootstrap 问题

原始 GitHub tarball 没有预生成的 configure 脚本，需要 bootstrap。但由于 autoreconf 失败（configure.ac 有语法问题），使用预生成的 configure 文件（通过 hints/bootstrap.sh）。

### LDFLAGS 配置

由于 glib 预编译包是静态库，configure 和链接时需要强制链接 libintl.a：

```bash
export LDFLAGS="-L$DEFAULT_PREFIX/lib $DEFAULT_PREFIX/lib/libintl.a"
./configure --prefix=$DEFAULT_PREFIX --without-magick --without-pstoedit --without-png
```

### 版本显示

编译版本显示为 0.40.0（源码内部版本号），与 GitHub release 标签 0.31.10 不一致。

## 已编译版本

| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| 0.31.10 | built | 2026-05-26 | 禁用 Magick/PNG，基础功能可用 |

## 安装验证

```bash
autotrace --version  # 输出: AutoTrace version 0.40.0
autotrace --help     # 查看支持的格式
```

## 参考链接

- GitHub: https://github.com/autotrace/autotrace
- 原始项目: http://autotrace.sourceforge.net/（已废弃）