# gocr

GOCR (JOCR) 是一个开源 OCR（光学字符识别）程序。

- **Homepage**: https://sourceforge.net/projects/jocr
- **License**: GPL-2.0
- **Category**: tools
- **Version**: 0.48

## 注意事项

- 较老的 autotools 项目（autoconf 2.59），需要 HMDFS umask 修复
- DESTDIR 安装模型需修正（原项目 DESTDIR=@prefix@ 不标准）