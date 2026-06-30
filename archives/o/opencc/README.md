# OpenCC (Open Chinese Convert)

## 简介

OpenCC 是一个开源的中文转换工具，支持简体中文、繁体中文、日语汉字等多种中文变体之间的转换。

## 功能特性

- 简体中文 ↔ 繁体中文转换
- 台湾繁体、香港繁体支持
- 日语汉字转换支持
- 多种转换模式（字符级、词组级）
- 高性能字典引擎（DartsDict）
- C++ 库 + 命令行工具

## 编译版本

### 1.1.9
- 编译日期：2026-05-26
- 编译器：Clang++ 15.0.4
- 构建系统：CMake
- 构建类型：静态库
- 状态：已构建

## 使用方法

```bash
# 简体转繁体
opencc -c s2t -i input.txt -o output.txt

# 繁体转简体
opencc -c t2s -i input.txt -o output.txt

# 管道模式
echo "简体中文" | opencc -c s2t
```

## 字典文件

预编译包包含以下字典：
- STCharacters.ocd2, STPhrases.ocd2（简→繁）
- TSCharacters.ocd2, TSPhrases.ocd2（繁→简）
- TWVariants.ocd2, HKVariants.ocd2（台湾/香港变体）
- JPVariants.ocd2（日语汉字）

## 许可证

Apache License 2.0

## 官方网站

https://github.com/BYVoid/OpenCC
