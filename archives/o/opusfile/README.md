# opusfile

> Opus 音频文件读取和解码库

## 简介

opusfile 提供了 Opus 音频文件的读取和解码功能，支持 Ogg Opus 文件格式（.opus 文件）。它依赖于 libopus 进行实际的音频解码，并提供高层 API 来简化 Opus 文件的处理。

opusfile 库主要用于：
- 读取和解码 .opus 文件
- 提供流式解码支持
- 支持Seeking（跳转到文件指定位置）
- 处理 Ogg Opus 文件的元数据

## OHOS 适配要点

- **依赖处理**：依赖 libopus 和 libogg，需先安装这些库
- **构建系统**：autotools，但可能遇到 E100 平台限制，推荐手动编译
- **配置选项**：可禁用 HTTP 支持（--disable-http）避开 OpenSSL 依赖
- **手动编译方法**：创建 config.h，直接用 clang 编译源文件

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| opus | 1.4 | Opus 音频编解码器库 |
| libogg | 1.3.5 | Ogg 容器格式库 |

## 功能验证

```bash
# pkg-config 验证
pkg-config --modversion opusfile
pkg-config --cflags opusfile
pkg-config --libs opusfile

# 检查库文件
ls ~/usr/local/lib/libopusfile.a
ls ~/usr/local/lib/libopusfile.so
```

## 参考

- [官方文档](https://opus-codec.org/docs/)
- [源码仓库](https://github.com/xiph/opusfile)