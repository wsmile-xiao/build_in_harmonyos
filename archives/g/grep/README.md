# GNU grep

GNU grep 是一个强大的文本搜索工具，用于在文件中搜索匹配指定模式的文本行。

## 描述
grep 搜索输入文件中匹配给定模式的行。默认情况下，grep 输出匹配的行。
支持基本正则表达式 (BRE)、扩展正则表达式 (ERE) 和 Perl兼容正则表达式 (PCRE)。

## 已编译版本
- 3.11 (2026-05-18)

## 功能特性
- 支持多种正则表达式语法
- PCRE2 支持 (Perl兼容正则表达式)
- 高性能搜索算法
- 递归目录搜索
- 多文件并行处理

## 使用示例
```bash
# 基本搜索
grep "pattern" file.txt

# Perl 正则表达式
grep -P "\d{3}-\d{4}" file.txt

# 递归搜索
grep -r "function" src/

# 显示行号
grep -n "error" log.txt
```

## 依赖
- pcre2 (Perl兼容正则表达式库)
