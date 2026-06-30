# Basis Universal

Basis Universal 是一个高性能纹理压缩编解码器，支持 GPU 纹理格式的超压缩。

## 描述

Basis Universal 可以将纹理压缩为 KTX2 格式，支持 BC7、ETC2、ASTC 等多种 GPU 纹理格式。它广泛应用于游戏引擎和 WebGL 内容交付。

## 已编译版本

- v2_1_0r (2026-05-30)

## 特性

- 纹理超压缩（transcoding to BC7/ETC2/ASTC）
- KTX2 格式支持
- 高性能编解码器
- WebGL 和游戏引擎兼容

## 使用方法

```bash
# 压缩纹理
basisu input.png -o output.ktx2
```