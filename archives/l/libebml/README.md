# libebml - Extensible Binary Meta Language library

## 简介

libebml 是一个 C++ 库，用于读写 EBML (Extensible Binary Meta Language) 格式的文件。EBML 是一种灵活的二进制格式，类似于 XML 但更高效。libebml 是 Matroska (MKV) 视频容器格式的基础库。

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.4.5 | built | 2026-05-20 |

## 依赖

无外部依赖。

## 用途

libebml 主要用于：
- Matroska (MKV) 文件的读写
- 作为 libmatroska 的依赖库
- 其他基于 EBML 格式的多媒体应用

## 相关软件

- libmatroska: Matroska 容器库（依赖 libebml）
- MKVToolNix: Matroska 工具集
- FFmpeg: 多媒体处理（可选依赖 libebml）

## 参考

- 主页: https://github.com/Matroska-Org/libebml
- 文档: https://matroska-org.github.io/libebml/