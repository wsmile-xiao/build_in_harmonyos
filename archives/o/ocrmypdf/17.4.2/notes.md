# OCRmyPDF 17.4.2 编译笔记

## 编译日期
2026-05-21

## 编译环境
- 平台: OpenHarmony
- Python: 3.12

## 构建系统
- 类型: Python 包（hatchling）
- 无需 configure/make

## 编译过程

### 1. 源码准备
源码已从 PyPI 下载：ocrmypdf-17.4.2.tar.gz
解压到：~/build_in_harmonyos_repo/tmp/builds/ocrmypdf-17.4.2/

### 2. 依赖分析
OCRmyPDF 是纯 Python 包，使用 hatchling 作为构建后端。
外部程序依赖（运行时）：
- Ghostscript (gs) - PDF 处理和 PDF/A 验证
- Tesseract OCR - OCR 文字识别引擎

Python 依赖（见 pyproject.toml）：
- deprecation>=2.1.0
- fpdf2>=2.8.0
- img2pdf>=0.5
- packaging>=20
- pdfminer.six>=20220319
- pi-heif
- pikepdf>=10
- Pillow>=10.0.1
- pluggy>=1
- pydantic>=2.12.5
- pypdfium2>=5.0.0
- rich>=13
- uharfbuzz>=0.53.2

### 3. 安装过程
```bash
# 使用 pip 安装到目标目录
export LD_LIBRARY_PATH=/data/service/hnp/python.org/python_3.12/lib:$HOME/usr/local/lib:$LD_LIBRARY_PATH
/data/service/hnp/python.org/python_3.12/bin/python3.12 -m pip install \
  --target=$HOME/usr/local/lib/python3.12/site-packages \
  ~/tmp/downloads/ocrmypdf-17.4.2.tar.gz --no-deps
```

### 4. 预编译包制作
创建了两个预编译包：
1. `ocrmypdf-17.4.2-ohos-aarch64.tar.gz` - 包含安装后的 Python 包（ocrmypdf 目录和 dist-info）
2. `ocrmypdf-17.4.2-py3-none-any.whl.tar.gz` - 包含 wheel 文件

## 补丁记录
无补丁 - OCRmyPDF 是纯 Python 包，安装过程中无需修改源码。

## 验证
安装成功，wheel 文件生成正常。

---
**编译结束**
**最终状态**: built
**编译日期**: 2026-05-21