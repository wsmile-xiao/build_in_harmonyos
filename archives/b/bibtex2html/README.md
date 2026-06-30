# bibtex2html

**软件描述**: BibTeX to HTML 转换器，将 BibTeX 格式的参考文献转换为美观的 HTML 页面。

**主页**: http://www.lri.fr/~filliatr/bibtex2html/

**许可证**: GNU GPL v2

**编程语言**: OCaml

## 功能概述

bibtex2html 是一组工具，用于从 BibTeX 格式的参考文献自动生成 HTML 文档。包含三个命令行工具：

- **bibtex2html**: 读取 BibTeX 文件并输出两个 HTML 文档（格式化引用 + 带链接的 BibTeX 原文）
- **bib2bib**: 过滤工具，读取一个或多个 BibTeX 文件，按条件过滤条目并输出
- **aux2bib**: 从 LaTeX 生成的 .aux 文件提取 BibTeX 引用（Perl 脚本）

## 版本索引

| 版本 | 状态 | 构建系统 | 编译日期 |
|------|------|----------|----------|
| 1.99 | built | autotools | 2026-06-18 |

## 编译依赖

- OCaml >= 3.07（本环境使用 4.14.2，字节码编译）
- bibtex 命令（完整 HTML 转换需要，可选）
