# byacc — Berkeley Yacc 解析器生成器

byacc（Berkeley Yacc）是一个公共领域的 LALR 解析器生成器，可替代原始 AT&T yacc。
它支持 btyacc（回溯 yacc）扩展。

## 版本

- **当前版本**: 20260126
- **历史版本**: 多个历史发布版本

## 功能描述

byacc 读取 Yacc 兼容的 `.y` 语法规范文件，并生成 C 语言解析器实现（`y.tab.c`）。
主要功能包括：

- 标准 LALR(1) 解析器生成
- 回溯扩展（btyacc 模式，使用 `-B` 选项）
- POSIX yacc 兼容性
- 纯（可重入）解析器支持

## 链接

- 源码: https://invisible-mirror.net/archives/byacc/
- 维护者: Thomas E. Dickey