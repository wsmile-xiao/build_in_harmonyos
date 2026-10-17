# LZHAM — OpenHarmony 软件档案

LZHAM 是面向高压缩率的无损数据压缩库，提供 C API 和 zlib 风格的编解码接口。

## 功能概述

- 内存和流式压缩/解压缩
- C API 与 zlib 风格 API
- CMake 构建和 Conan 消费

## OHOS 适配

在 OpenHarmony aarch64 上，LZHAM 适配需要把上游内部构建目标整理为可安装的库，并保留可执行的上游测试。上游提供的 ANSI C/C++ 路径可用于不依赖平台线程与原子实现的构建；各版本的具体选项、补丁和设备验证结果以对应版本目录为准。

## 依赖关系

不依赖其他 Conan 包；只使用 C/C++ 运行时和标准系统接口。

## 参考资料

- [LZHAM GitHub](https://github.com/richgel999/lzham_codec)
- [LZHAM v1_0_release tags](https://github.com/richgel999/lzham_codec/tags)
