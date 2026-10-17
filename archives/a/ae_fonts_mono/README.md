# ae_fonts_mono

Arabeyes 阿拉伯语等宽字体（10x21），纯字体数据包。

## 描述

ae_fonts_mono 是 Arabeyes 项目发布的阿拉伯语等宽位图字体，包含 10x21.bdf 与
10x21.pcf 两个字体文件（ISO10646 编码，4491 字形）。该包为纯字体数据包，
FreeBSD port 标记 NO_BUILD=yes，无任何构建系统、可执行文件或库。

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 1.0 | built | 2026-08-05 |

## 构建信息

- **构建系统**: custom（无构建，NO_BUILD=yes）
- **许可证**: Public domain（BDF 头 COPYRIGHT "Public domain font. Share and enjoy."）
- **源码**: https://downloads.sourceforge.net/project/arabeyes/Fonts/ae_fonts/ae_fonts_mono.tar.bz2
- **SHA256**: 62990ea66e05b9a0ec46490e0adbb69a1c83977bd9dfdc7a2d6ffd208e6ec668

## 产物

安装路径: `share/fonts/ae_fonts_mono/`

| 文件 | 大小 | 说明 |
|------|------|------|
| 10x21.bdf | 841126 B | BDF 位图字体（4491 字形） |
| 10x21.pcf | 626844 B | PCF 位图字体 |

另提供 `lib/pkgconfig/ae_fonts_mono.pc` 声明 fontdir 变量。

## 构建依赖

无。

## 平台适配补丁

无（纯数据包，无需补丁）。

## 参考资料

- 上游项目: https://www.arabeyes.org/
- SourceForge 镜像: https://downloads.sourceforge.net/project/arabeyes/Fonts/ae_fonts/
