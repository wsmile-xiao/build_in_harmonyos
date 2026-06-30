# cmark

## 简介

cmark 是 CommonMark (Markdown) 规范的 C 语言实现，提供高效的 Markdown 解析和渲染库。它可以将 Markdown 文本转换为 HTML、XML、LaTeX、groff man 等多种格式。

## 基本信息

- **官方网站**: https://github.com/commonmark/cmark
- **构建系统**: CMake
- **编程语言**: C
- **许可证**: BSD-2-Clause

## 特性

- 快速、高效、可移植的 Markdown 解析器
- 符合 CommonMark 规范 0.31
- 支持多种输出格式（HTML, XML, LaTeX, groff man）
- 提供 C API 和命令行工具
- 小巧的代码库，易于集成

## 编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.31.2 | built | 2026-05-21 | 首次编译，静态库版本 |

## 依赖

无外部库依赖，仅需 cmake 构建工具。

## 用法

### 命令行工具

```bash
# Markdown 转 HTML
echo "# Hello" | cmark -t html

# Markdown 转 XML
echo "# Hello" | cmark -t xml

# Markdown 转 LaTeX
echo "# Hello" | cmark -t latex
```

### C API

```c
#include <cmark.h>

// 解析 Markdown 文本
cmark_node *document = cmark_parse_document(text, strlen(text), CMARK_OPT_DEFAULT);

// 渲染为 HTML
char *html = cmark_render_html(document, CMARK_OPT_DEFAULT);

// 清理
cmark_node_free(document);
free(html);
```

## 注意事项

1. 静态库版本（BUILD_SHARED_LIBS=OFF）避免 ELF 签名问题
2. Python 测试需要 libffi.so.8（核心功能已通过 C API 测试验证）
3. CMake 在 HarmonyOS 上提示系统未知，不影响编译结果