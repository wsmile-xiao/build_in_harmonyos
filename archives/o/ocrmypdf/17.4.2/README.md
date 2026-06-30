# OCRmyPDF

OCRmyPDF 为扫描的 PDF 文件添加 OCR 文字层，使其可搜索和复制粘贴。

## 主要功能

- 为 PDF 文件添加可搜索的 OCR 文字层
- 支持多语言 OCR（通过 Tesseract）
- 自动旋转校正和倾斜校正
- 生成 PDF/A 格式输出
- 支持图像优化和压缩
- 多核并行处理

## 外部依赖

- **Ghostscript**: PDF 处理和 PDF/A 验证
- **Tesseract OCR**: OCR 文字识别引擎

## 安装

```bash
pip install ocrmypdf
```

## 使用示例

```bash
# 基本 OCR 处理
ocrmypdf input.pdf output.pdf

# 多语言支持
ocrmypdf -l eng+fra input.pdf output.pdf

# 生成 PDF/A 格式
ocrmypdf --output-type pdfa input.pdf output.pdf

# 自动旋转校正
ocrmypdf --rotate-pages input.pdf output.pdf
```

## 许可证

MPL-2.0 (Mozilla Public License 2.0)

## 链接

- 官方文档: https://ocrmypdf.readthedocs.io/
- 源代码: https://github.com/ocrmypdf/OCRmyPDF