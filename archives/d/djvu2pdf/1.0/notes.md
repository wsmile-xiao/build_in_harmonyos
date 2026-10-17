# djvu2pdf 1.0 适配笔记

## 编译环境
- 构建系统: makefile (自定义 Makefile)
- 编译日期: 2026-08-06
- 编译器: 无编译器（Shell脚本项目）
- 状态: built

## 编译步骤

djvu2pdf 是一个 Shell 脚本工具，不需要编译。安装步骤如下：

1. 源码没有提供 Makefile，因此创建了一个简单的 Makefile 用于安装脚本文件
2. `make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX` 将脚本安装到 staging 目录
3. `make install PREFIX=$DEFAULT_PREFIX` 将脚本安装到本地 $DEFAULT_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码无 Makefile/configure | Shell脚本项目，非传统编译项目 | 创建 Makefile 处理脚本安装 |
| 2 | 依赖不可用 | ddjvu/djvused/djvu2hocr/tiffsplit/pdfbeads 未预编译 | 作为脚本工具打包，运行时依赖预装环境 |

## 源码修改

- 新增 Makefile：简单的安装 Makefile，用于将 djvu2pdf 和 djvu2pdf_toc_parser.py 安装到 bin 目录

## 依赖版本

运行时依赖（需预装）：
- djvulibre: 提供 ddjvu、djvused 命令
- djvu2hocr: 提供 OCR 文本提取
- libtiff: 提供 tiffsplit 命令
- pdfbeads: 提供 PDF 合成功能

## 验证结果

```bash
bash -n $PREFIX/bin/djvu2pdf && echo "djvu2pdf: syntax OK"
python3 -c "import py_compile; py_compile.compile('$PREFIX/bin/djvu2pdf_toc_parser.py', doraise=True)" && echo "djvu2pdf_toc_parser.py: syntax OK"
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| djvu2pdf | 1561 字节 | DjVu 转 PDF Shell 脚本 |
| djvu2pdf_toc_parser.py | 2765 字节 | TOC 解析 Python 脚本 |

## 注意事项

- djvu2pdf 是 Shell 脚本工具，运行时需要依赖环境（djvulibre、tiffsplit、pdfbeads 等）
- 此包仅提供脚本本身，不包含运行时依赖
---

**编译结束**: 2026-08-06 07:24
**最终状态**: built
