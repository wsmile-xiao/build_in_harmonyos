# Poppler

Poppler 是一个基于 xpdf PDF 渲染库的开源 PDF 渲染库，用于渲染和操作 PDF 文件。

## 基本信息

- **官网**: https://poppler.freedesktop.org/
- **源码**: https://poppler.freedesktop.org/releases.html
- **构建系统**: cmake
- **依赖**: freetype2, fontconfig, libjpeg, libpng, libtiff, libopenjpeg2, lcms2, zlib, curl

## 编译版本

| 版本 | 状态 | C++ 标准 | 备注 |
|------|------|---------|------|
| 24.03.0 | published | C++17 | 基础版本 |
| 25.11.0 | built | C++20 | 需要 17 个补丁适配 std::ranges |

## 注意事项

- poppler 25.12.0+ 强制要求 C++23，当前系统 Clang 15 仅支持 C++20
- 如需编译新版本，需升级编译器到 Clang 16+ 或 GCC 12+

## 工具

编译产物包含以下命令行工具：
- pdftotext - PDF 转文本
- pdfinfo - PDF 信息查看
- pdftoppm - PDF 转图片
- pdfimages - 提取 PDF 图片
- pdfseparate - 分离 PDF 页面
- pdfunite - 合并 PDF
- pdfattach/pdfdetach - PDF 附件操作
- pdffonts - PDF 字体信息
- pdftohtml - PDF 转 HTML
- pdftops - PDF 转 PostScript
- pdfsig - PDF 签名验证