# pdftoipe

pdftoipe 是一个将 PDF 文件转换为 Ipe（可扩展绘图编辑器）XML 格式的工具。

## 描述
pdftoipe 使用 poppler 库解析 PDF 文件，将其内容转换为 Ipe 编辑器可以编辑的 XML 格式。适用于需要在 Ipe 中编辑 PDF 图形的场景。

## 已编译版本
- latest (2026-05-26)

## 依赖
- poppler 25.11.0

## 使用方法
```bash
# 转换 PDF 到 Ipe XML
pdftoipe input.pdf output.xml
```