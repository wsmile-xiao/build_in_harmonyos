# zathura-pdf-mupdf

zathura-pdf-mupdf 是 zathura 文档查看器的 MuPDF PDF 渲染插件。

## 功能概述

- 使用 MuPDF 渲染引擎显示 PDF 文件
- 支持高精度 PDF 渲染
- 与 zathura 深度集成（键盘驱动界面）

## OHOS 适配

- **构建系统**: meson
- **无源码修改**: 所有调整通过构建配置完成
- **mupdf静态链接**: libmupdf.a 链入插件，体积较大（~50MB）

## 运行依赖

- zathura (文档查看器)
- mupdf (PDF渲染引擎)

## 参考资料

- 源码: https://github.com/pwmt/zathura-pdf-mupdf
- 版本: 2026.05.10
