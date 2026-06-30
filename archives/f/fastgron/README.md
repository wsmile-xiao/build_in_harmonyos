# fastgron

## 简介

fastgron 是一个高性能的 JSON 到 GRON 格式转换工具。GRON 格式将 JSON 数据展平为每行一个键值对，便于 grep、sed 等文本工具处理。

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.7.7 | built | 2026-06-26 |

## 构建信息

- **构建系统**: CMake
- **语言**: C++20
- **许可证**: MIT
- **依赖**: 无（内嵌 simdjson，CURL 为可选依赖已禁用）
- **产物**: bin/fastgron（终端工具，静态链接）

## 链接

- **主页**: https://github.com/adamritter/fastgron
- **源码**: https://github.com/adamritter/fastgron/archive/refs/tags/v0.7.7.tar.gz
