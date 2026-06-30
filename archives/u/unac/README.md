# unac — C 语言去重音字符库

## 简介

unac 是一个 C 语言库和命令行工具，用于从文本中去除重音字符（accented characters）。它基于 Unicode 字符数据将带重音的字符映射为对应的无重音字符，支持多种编码格式（通过 iconv 转换）。

## 功能

- **libunac 库**: 提供 `unac_string()` 等 API，用于编程方式去除字符串中的重音
- **unaccent 命令行工具**: 从标准输入或命令行参数去除重音，支持多种字符集编码

## 编译状态

| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| 1.8.0 | published | 2026-06-16 | autotools 编译，无需补丁 |

## API 概述

```c
#include <unac.h>

// 去除字符串重音
int unac_string(const char *charset, const char *in, int in_length, char **out, int *out_length);

// 设置调试回调
void unac_debug_callback(unac_debug_t callback);
```

## 命令行用法

```bash
# 基本用法
unaccent UTF-8 "café"          # 输出: cafe
echo "été" | unaccent UTF-8    # 输出: ete

# 查看版本
unaccent                       # 显示版本号和帮助信息
```

注意：unaccent 不支持 `--version` 选项，需不带参数运行查看版本信息。

## 依赖

- iconv（系统自带）

## 许可证

GPL v2+
