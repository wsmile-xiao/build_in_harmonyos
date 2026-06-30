# pdfcpu

pdfcpu 是一个用 Go 语言编写的 PDF 处理库和命令行工具，支持 PDF 的验证、优化、加密/解密、合并、拆分、旋转、裁剪、添加水印等操作。

## 已编译版本
- 0.12.1 (2026-05-25)

## 功能特点
- PDF 验证与优化
- PDF 加密与解密
- PDF 合并与拆分
- PDF 页面旋转、裁剪
- 添加水印
- 提取页面内容
- 支持 PDF/A 规范

## 使用方法
```bash
# 验证 PDF
pdfcpu validate input.pdf

# 合并 PDF
pdfcpu merge input1.pdf input2.pdf output.pdf

# 拆分 PDF
pdfcpu split input.pdf outputDir

# 加密 PDF
pdfcpu encrypt input.pdf output.pdf

# 添加水印
pdfcpu watermark add -m "CONFIDENTIAL" input.pdf output.pdf
```

## 链接
- 官方网站: https://pdfcpu.io
- 源码下载: https://github.com/pdfcpu/pdfcpu/archive/refs/tags/v0.12.1.tar.gz