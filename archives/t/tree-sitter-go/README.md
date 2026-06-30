# tree-sitter-go

Go language grammar for tree-sitter parser generator.

## 版本信息
- 当前版本: 0.25.0
- 发布日期: 2026-06-15
- 官网: https://github.com/tree-sitter/tree-sitter-go

## 描述
tree-sitter-go 是 tree-sitter 解析器生成器的 Go 语言语法模块，提供高效的 Go 语言语法解析能力。

主要功能：
- Go 语言语法解析
- 语法树生成
- 与 tree-sitter 核心库集成

## 编译状态
- 鸿蒙难度: 🟢 (简单)
- 构建系统: Makefile
- 编译器: gcc
- 状态: built

## 依赖
- 无外部依赖

## 已知问题
- 平台缺少 `install` 命令：需手动使用 mkdir + cp + ln 替代
- G0 干净构建验证跳过：OpenHarmony SDK clang 强制使用 lld 链接器，lld 需要 libxml2.so.16，在子进程中可能无法访问（平台限制）

## 使用方式
```bash
# 使用 pkg-config
gcc myapp.c $(pkg-config --cflags --libs tree-sitter-go)

# 手动链接
gcc myapp.c -I$DEFAULT_PREFIX/include -L$DEFAULT_PREFIX/lib -ltree-sitter-go
```