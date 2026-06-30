# md2pdf

md2pdf 是一个将 Markdown 文件转换为 PDF 的命令行工具，支持自定义样式、代码高亮和 YAML front matter。

## 已编译版本
- 3.1.1 (2026-05-25)

## 功能特点
- Markdown → PDF 转换
- 自定义 CSS 样式
- 代码语法高亮（Pygments）
- YAML front matter 支持
- 支持多种 Markdown 扩展（Pymdown Extensions）

## 使用方法
```bash
# 设置 PYTHONPATH
export PYTHONPATH=$HOME/usr/local/lib/python3.12/site-packages

# 转换 Markdown 为 PDF
md2pdf input.md

# 指定输出文件
md2pdf input.md -o output.pdf

# 查看帮助
md2pdf --help
```

## 链接
- 源码下载: https://pypi.org/packages/source/m/md2pdf/md2pdf-3.1.1.tar.gz