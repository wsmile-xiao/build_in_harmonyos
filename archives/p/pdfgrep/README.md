# pdfgrep

## 简介
pdfgrep 是一个在 PDF 文件中搜索文本的工具，功能类似于 grep。它支持正则表达式搜索、递归搜索目录中的 PDF 文件等特性。

## 编译版本
- 版本: 2.2.0
- 状态: built
- 编译系统: autotools（手动编译）

## 功能特点
- 支持在 PDF 文件中搜索文本（类似 grep）
- 支持正则表达式匹配（PCRE）
- 支持递归搜索目录中的 PDF 文件
- 支持页码范围搜索
- 支持颜色高亮输出

## 依赖
- poppler-cpp 23.12.0
- poppler 23.12.0
- libgcrypt 1.11.0
- libgpg-error 1.55（静态链接）
- libpcre2-8 10.40

## 使用方法
```bash
# 搜索 PDF 中的关键词
pdfgrep "pattern" file.pdf

# 递归搜索目录中的所有 PDF
pdfgrep -r "pattern" /path/to/docs/

# 使用正则表达式搜索
pdfgrep -P "regex" file.pdf

# 显示匹配行所在页码
pdfgrep -n "pattern" file.pdf
```

## 链接
- 官方网站: https://pdfgrep.org
- 源码下载: https://pdfgrep.org/download/pdfgrep-2.2.0.tar.gz

## 注意事项
- 运行时需要确保 poppler、pcre2 等依赖库在 LD_LIBRARY_PATH 中可找到
- config.h 是手动创建的（替代了 autotools configure），未来升级版本需重新检测功能宏