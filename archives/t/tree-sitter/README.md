# tree-sitter

tree-sitter 是一个增量式解析系统，用于编程工具开发。它提供了一个高效的解析器生成器和一个增量式解析库，可以在编辑过程中快速重新解析源代码。

## 描述

tree-sitter 主要特性：
- **增量解析**：源代码修改后，只需重新解析受影响的部分
- **错误恢复**：即使源代码有语法错误，也能生成有用的语法树
- **语言无关**：支持多种编程语言的语法定义
- **多语言绑定**：提供 C、Rust、Python、JavaScript、WASM 等绑定

## 已编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.25 | built | 2026-06-05 |

## 使用说明

tree-sitter 编译为库文件（无命令行工具）：
- **libtree-sitter.a**：静态库
- **libtree-sitter.so**：共享库

使用 pkg-config 链接：
```bash
pkg-config --cflags tree-sitter  # -I/storage/Users/currentUser/usr/local/include
pkg-config --libs tree-sitter    # -L/storage/Users/currentUser/usr/local/lib -ltree-sitter
```

## 下游项目

tree-sitter 库可用于：
- Neovim 编辑器（语法高亮）
- Helix 编辑器
- Atom 编辑器
- 自定义解析工具

## 相关链接

- 官网：https://tree-sitter.github.io/tree-sitter/
- GitHub：https://github.com/tree-sitter/tree-sitter
