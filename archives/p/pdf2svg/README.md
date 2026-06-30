# pdf2svg

pdf2svg 是一个将 PDF 文件转换为 SVG 格式的工具。

## 描述
pdf2svg 使用 poppler-glib 和 cairo 库将 PDF 文件的每一页转换为独立的 SVG 文件。适用于需要将 PDF 内容以矢量图形格式展示的场景。

## 已编译版本
- v0.2.4 (2026-05-25)

## 依赖
- poppler 25.11.0 (含 poppler-glib)
- cairo 1.18.4
- glib2 2.84.0

## 使用方法
```bash
# 转换 PDF 所有页为 SVG
pdf2svg input.pdf output.svg

# 转换特定页
pdf2svg input.pdf output.svg 3

# 转换所有页为独立 SVG 文件
pdf2svg input.pdf output-%d.svg all
```