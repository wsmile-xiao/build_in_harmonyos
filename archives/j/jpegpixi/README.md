# jpegpixi

JPEG 像素级修复/插值工具（interpolate pixels in JPEG images）。读取 JPEG 文件，
按坐标插值修复坏点/死像素后重编码输出，仅对受影响块重新压缩，图像其余部分保持
原始数据不变。附带的 `jpeghotp` 可将 hotpixel 坐标写入 JPEG 扩展段。

- 上游主页: http://www.zero-based.org/software/jpegpixi/ （Martin Dickopp，2002-2005）
- 源码: Debian 池 `jpegpixi_1.1.1.orig.tar.gz`（上游原样 tarball；上游站点仅 http，
  按 R39 采用 https 权威镜像源）
- 许可证: GPL-2.0-or-later
- 语言: C（autotools）
- 产物: `bin/jpegpixi`（主命令）、`bin/jpeghotp`
- 依赖: libjpeg/10（ohpcd 制品仓）
