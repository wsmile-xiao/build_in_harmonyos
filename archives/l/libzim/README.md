# libzim

## 描述

libzim 是 ZIM 文件格式的参考实现，用于存储离线内容（如维基百科离线包）。

## 主要功能

- 读取和写入 ZIM 格式文件
- 高效的压缩和索引
- 支持多媒体内容

## 依赖

- lz4
- zstd
- xz-utils (liblzma)
- zlib

## OpenHarmony 适配

编译方式：meson + ninja

## 使用说明

```c
#include <zim/zim.h>
#include <zim/archive.h>

zim::Archive archive("example.zim");
// 使用 archive 对象访问 ZIM 文件内容
```

## 版本

- 9.7.0 (2026-05-26): 编译成功