# zathura-pdf-poppler

zathura-pdf-poppler 是 zathura 文档查看器的 Poppler PDF 渲染插件。

## 功能概述

- 使用 Poppler 渲染引擎显示 PDF 文件
- Poppler 渲染质量稳定，兼容性好
- 与 zathura 深度集成（键盘驱动界面）

## OHOS 适配

- **构建系统**: meson
- **无源码修改**: 所有调整通过构建配置和系统依赖处理完成
- **前置依赖**: girara-gtk3 0.4.5 + zathura 0.5.14 手动编译

## 运行依赖

- zathura (文档查看器)
- poppler (PDF渲染引擎)

## 参考资料

- 源码: https://github.com/pwmt/zathura-pdf-poppler
- 版本: 0.3.4
