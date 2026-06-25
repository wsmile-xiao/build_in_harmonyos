# html2text

Advanced HTML-to-text converter.

## 描述

html2text 是一个高级的 HTML 到文本转换工具，能够将 HTML 文档转换为格式化的 ASCII 文本。

## 版本

- 2.4.0 (2026-05-19)

## 功能

- HTML 转 ASCII 文本
- 支持多种编码（ASCII, ISO-8859-1, UTF-8）
- 表格渲染
- 链接提取
- 自定义宽度设置

## 使用方法

```bash
html2text [选项] <HTML文件>
```

常用选项：
- `-help`: 显示帮助
- `-version`: 显示版本
- `-width <w>`: 设置输出宽度
- `-links`: 显示链接
- `-o <file>`: 输出到文件

## 编译信息

- 构建系统：autotools
- 编译器：clang/clang++
- 平台：HarmonyOS (aarch64)
