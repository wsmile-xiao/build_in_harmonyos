# fonts-encodings

X.Org 字体编码数据包，提供字体编码表（encoding tables）用于 X.Org 字体系统。

## 描述

fonts-encodings 包含 X.Org 字体系统使用的编码定义文件。这些编码文件将字体编码
名称映射到 Unicode，支持多种编码标准包括 Adobe、IBM、ISO、Microsoft 和 CJK 编码。

该包为纯数据包，不生成任何二进制可执行文件或库文件。产物为 gzip 压缩的 .enc.gz
编码文件和 encodings.dir 索引文件。

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 1.1.0 | published | 2026-06-26 |

## 构建信息

- **构建系统**: autotools (configure + make)
- **许可证**: LicenseRef-Homebrew-public-domain
- **源码**: https://www.x.org/archive/individual/font/encodings-1.1.0.tar.xz
- **SHA256**: 9ff13c621756cfa12e95f32ba48a5b23839e8f577d0048beda66c67dab4de975

## 产物

安装路径: `share/fonts/X11/encodings/`

| 目录 | 内容 | 文件数 |
|------|------|--------|
| encodings/ | 小编码文件 + encodings.dir | 35 (34 .enc.gz + 1 .dir) |
| encodings/large/ | 大编码文件 + encodings.dir | 17 (16 .enc.gz + 1 .dir) |
| lib/pkgconfig/ | fonts-encodings.pc | 1 |

支持的编码包括:
- Adobe: dingbats, standard, symbol
- IBM: cp437, cp850, cp852, cp866
- ISO: 8859-6.16, 8859-6.8x, 8859-11, 8859-13, 8859-14, 8859-16
- Microsoft: cp1250-cp1258, win3.1
- CJK: big5, cns11643-1/2/3, gb18030, gb2312, gbk, jisx0201/0208/0212, ksc5601
- 其他: armscii-8, ascii-0, dec-special, mulearabic-0/1/2, mulelao-1, suneu-greek, tcvn-0, tis620-2, viscii1.1-1

## 构建依赖

| 依赖 | 版本 | 来源 |
|------|------|------|
| mkfontscale | wrapper | 手动创建 |
| font-util | 1.4.1 | 预编译包 |
| util-macros | 1.20.2 | 预编译包 |
| gzip | 系统自带 | /usr/bin/gzip |

## 平台适配补丁

| 补丁 | 说明 |
|------|------|
| 0001-config.guess.patch | 添加 HarmonyOS 平台检测 |
| 0002-configure.patch | 修复 HMDFS umask 077 权限问题 |
