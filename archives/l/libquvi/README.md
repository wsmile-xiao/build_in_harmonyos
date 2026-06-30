# libquvi

**简介**: libquvi 是一个用于解析媒体流URL的库，主要用于从各种视频网站提取视频链接。

**类别**: 网络库

**版本**: 0.9.4

**编译状态**: built

**编译日期**: 2026-06-11

## 编译信息

- **构建系统**: autotools
- **编译器**: clang/clang++
- **依赖**: libproxy, lua, curl, glib

## 补丁

本版本包含3个补丁，修复了头文件路径问题：
- 0001-src-api-free.c.patch
- 0002-src-api-new.c.patch
- 0003-src-curl-autoproxy.c.patch

## 注意事项

- 头文件路径修复：`#include <proxy.h>` 改为 `#include <libproxy/proxy.h>`