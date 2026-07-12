# poppler

PDF 渲染库，提供 PDF 文档处理功能。

## 项目信息

- **主页**: https://poppler.freedesktop.org/
- **源码**: https://gitlab.freedesktop.org/poppler/poppler
- **许可证**: GPL-2.0-or-later

## 描述

Poppler 是一个基于 xpdf PDF 渲染库的开源 PDF 渲染库，提供命令行工具和编程接口。

## 主要功能

- PDF 文档解析和渲染
- PDF 转文本（pdftotext）
- PDF 转 HTML（pdftohtml）
- PDF 转 PostScript（pdftops）
- PDF 转图片（pdftoppm）
- PDF 图像提取（pdfimages）
- PDF 字体分析（pdffonts）
- PDF 信息查询（pdfinfo）
- PDF 页面分离（pdfseparate）
- PDF 合并（pdfunite）
- PDF 附件处理（pdfattach/pdfdetach）

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁 | 说明 |
|------|------|---------|------|------|
| 25.12.0 | published | 2026-07-08 | 37 | C++23 std::ranges 兼容性修复 + OHOS 平台适配 |

## 依赖

- freetype/2.14.3@ohpcd/stable (Conan)
- fontconfig: 绕过 (-DFONT_CONFIGURATION=generic)
- liblcms2 2.16: 系统预装

## 编译环境

- Clang 15.0.4 / CMake 4.1.2 / Conan 2.29.1 / Python 3.12.9
- Profile: ohos-aarch64 (os=OHOS, arch=armv8, compiler=clang/15, cppstd=17, libcxx=libc++)

## CI 合规

- L0: PASS | L1: PASS | L2: SKIP (平台限制) | L4: WARN (误报) | L5: PASS
- 总体: SUCCESS

## 使用说明

```bash
# 查看 PDF 信息
pdfinfo document.pdf

# 提取文本
pdftotext document.pdf output.txt

# 转换为 HTML
pdftohtml document.pdf output.html

# 提取图像
pdfimages -all document.pdf image_prefix

# 转换为图片
pdftoppm -png document.pdf output_prefix
```
