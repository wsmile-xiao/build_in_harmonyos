# pdf2image

**pdf2image** 是一个轻量级 Python 包，用于将 PDF 文件转换为 Pillow (PIL) 图像列表。它是 poppler-utils (pdftoppm、pdftocairo) 命令行工具的 Python 封装。

## 功能概述

- `convert_from_path()` — 从 PDF 文件路径转换为图像列表
- `convert_from_bytes()` — 从 PDF 字节流转换为图像列表
- `pdfinfo_from_path()` — 获取 PDF 文件的元信息（页数等）
- `pdfinfo_from_bytes()` — 从字节流获取 PDF 元信息
- 支持多线程转换、透明背景、灰度输出等多种选项

## OHOS 适配

- **纯 Python 包**：无需编译器，使用 `setup.py install` 安装
- **运行时依赖**：需要 poppler-utils 提供的 pdftoppm/pdftocairo/pdfinfo 命令
- **Python 依赖**：需要 Pillow 包
- **PYTHONPATH**：安装后需设置 `PYTHONPATH` 包含 `$DEFAULT_PREFIX/lib/python3.12/site-packages`

## 已知问题

- pdf2image 本身不包含原生二进制，功能完全依赖于 poppler-utils 的命令行工具
- 若系统未安装 poppler-utils，调用 convert_from_path 等函数会抛出 PDFInfoNotInstalledError

## 依赖关系

- **运行时依赖**：poppler-utils (pdftoppm, pdftocairo, pdfinfo)
- **Python 依赖**：Pillow (PIL)

## 参考资料

- PyPI: https://pypi.org/project/pdf2image/
- GitHub: https://github.com/Belval/pdf2image