# djvu2pdf

djvu2pdf 是一个将 DjVu 格式文件转换为 PDF 格式的 Shell 脚本工具。

## 描述

djvu2pdf 使用 ddjvu 和其他 DjVu 工具将 DjVu 文件转换为 PDF 格式，支持 OCR 文本保留和页面布局保持。它是处理 DjVu 文档的常用转换工具。

## 已编译版本

- 1.0 (2026-05-27)

## 依赖

- djvulibre (ddjvu, djvused 命令)
- libtiff (tiffsplit 命令)
- djvu2hocr (OCR 文本提取)
- pdfbeads (PDF 合成)

## OHOS 适配说明

- Shell 脚本项目，无需编译
- 创建自定义 Makefile 处理安装流程

## 使用方法

```bash
# 转换 DjVu 文件为 PDF
djvu2pdf input.djvu
```