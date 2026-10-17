# cmark-gfm

## 软件简介

**cmark-gfm** 是 GitHub Flavored Markdown (GFM) 的 C 语言实现，基于 CommonMark 规范。它是 cmark 的扩展版本，增加了对 GitHub 特有 Markdown 功能的支持。

## 当前版本

- **版本**: 0.29.0.gfm.13
- **状态**: built (Conan 配方已验证，待发布)
- **编译日期**: 2026-08-06

## 主要功能

### GitHub Flavored Markdown 解析
- 完整支持 CommonMark 规范
- GitHub 扩展语法支持：
  - 表格（Tables）
  - 任务列表（Task lists）
  - 删除线（Strikethrough）
  - 自动链接（Autolinks）
  - 代码高亮提示

### 核心组件

1. **libcmark-gfm** - 核心解析库
   - 提供 C API 接口
   - 支持共享库和静态库

2. **libcmark-gfm-extensions** - 扩展库
   - 提供 GFM 扩展功能
   - 包含表格、任务列表等处理器

3. **cmark-gfm** - 命令行工具
   - Markdown 转 HTML
   - 支持多种输出格式
   - 可加载扩展模块

## 技术特性

- **构建系统**: CMake
- **编译器**: Clang 15.0.4
- **平台**: OpenHarmony (鸿蒙)
- **架构**: aarch64

## 使用示例

### 命令行工具

```bash
# 基本转换
echo "# Hello World" | cmark-gfm

# 指定输出格式
cmark-gfm -t html input.md

# 启用扩展
cmark-gfm --extension table input.md
```

### C API 使用

```c
#include <cmark-gfm.h>
#include <cmark-gfm-core-extensions.h>

// 解析 Markdown 文档
cmark_node *document = cmark_parse_document(markdown_text, strlen(markdown_text), CMARK_OPT_DEFAULT);

// 转换为 HTML
char *html = cmark_render_html(document, CMARK_OPT_DEFAULT);
printf("%s\n", html);

// 清理资源
cmark_node_free(document);
free(html);
```

## 编译说明

本软件已在 OpenHarmony 平台成功编译，具体编译配置和补丁详见版本级归档目录。

### 注意事项

1. **CMake 版本兼容性**: 需要 CMake 3.5+（补丁已修复 3.0 版本要求）
2. **扩展库路径**: cmark-gfm 使用相对路径 `../extensions/` 加载扩展库，预编译包需要正确设置 RPATH
3. **测试限制**: 部分测试需要加载共享库，鸿蒙平台要求 ELF 签名

## 相关链接

- [GitHub 仓库](https://github.com/github/cmark-gfm)
- [CommonMark 规范](https://commonmark.org/)
- [GitHub Flavored Markdown 规范](https://github.github.com/gfm/)

## 许可证

BSD 2-Clause License