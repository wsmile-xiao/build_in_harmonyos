# rename

## 简介

rename 是一个 Perl 编写的文件批量重命名工具，支持正则表达式和多种操作模式。

## 特性

- 支持正则表达式替换
- 支持字符串替换
- 支持多种操作模式（link、symlink、rename）
- 支持编码转换
- 支持 man 页面

## 依赖

- Perl 5.x+
- Pod::Usage (Perl 内置)

## 使用示例

```bash
# 简单替换
rename -s .txt .md *.txt

# 正则表达式
rename 's/old/new/' *.txt

# 查看帮助
rename -h
```

## 版本历史

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.601 | published | 2026-06-05 |

## 来源

- Homepage: http://plasmasturm.org/code/rename
- Source: https://github.com/ap/rename
