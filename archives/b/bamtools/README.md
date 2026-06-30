# bamtools

## 简介

bamtools 是一个用于处理 BAM (Binary Alignment/Map) 文件的 C++ 工具库和命令行工具集。BAM 是生物信息学中用于存储序列比对数据的标准格式。

## 功能

- **BAM 文件读写**: 提供高效的 BAM 文件读取和写入 API
- **命令行工具**: 包括 convert、count、coverage、filter、header、index、merge、sort、split、stats 等功能
- **API 库**: 提供 C++ API 用于自定义 BAM 文件处理程序

## 主要组件

- `bamtools`: 命令行工具
- `libbamtools.a`: 静态库（提供 C++ API）
- 头文件: BamAlignment.h, BamReader.h, BamWriter.h 等

## 依赖

- zlib (压缩支持)
- libc++ (C++ 标准库)

## 来源

- GitHub: https://github.com/pezmaster31/bamtools
- 最新版本: v2.5.3 (2025-05-18)

## 授权

MIT License