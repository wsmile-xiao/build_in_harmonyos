# xmltoman

XML 到 man page 的转换工具——基于 Perl 的轻量级工具，将 XML 文档转换为 groff man page 格式和 HTML。

## 简介

xmltoman 是一个轻量级实用工具，将遵循其自有 DTD 格式的 XML 文件转换为传统 Unix man page（groff 格式）。同时提供 `xmlmantohtml` 用于将相同 XML 格式转换为 HTML（使用 xsltproc）。

## 主要功能

- `xmltoman`: 将 XML 转换为 man page（groff）格式
- `xmlmantohtml`: 将 XML 转换为 HTML 格式（可选依赖 xsltproc）
- 包含用于 XML man page 标记的简单 DTD
- 包含用于 HTML 生成的 XSLT 样式表和 CSS

## 运行时依赖

- Perl 5.x 及 XML::Parser 模块（必需）
- xsltproc（可选，用于 xmlmantohtml 的 HTML 输出）

## 版本

| 版本 | 日期 | 状态 | 备注 |
|------|------|------|------|
| 0.4 | 2026-06-11 | published | 简单 Makefile 项目，需修复 shebang 路径 |

## OpenHarmony/HarmonyOS 平台适配要点

- Perl shebang 需从 `#!/usr/bin/perl` 修改为平台实际 Perl 路径 `#!/storage/Users/currentUser/usr/local/bin/perl -w`
- 需预先安装 XML::Parser Perl 模块（依赖 expat 库）
- 无编译步骤——纯 Perl 脚本工具，仅需修复 shebang 和 `make install`

## 补丁列表

- 0001-xmlmantohtml.patch: 修复 xmlmantohtml 的 shebang 路径
- 0002-xmltoman.patch: 修复 xmltoman 的 shebang 路径