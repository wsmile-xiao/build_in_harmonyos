# apngasm

apngasm 是一个 APNG（Animated PNG）组装器，将一系列图像合成为动画 PNG 文件。

## 描述

apngasm 支持将多帧 PNG 图像合成为 APNG 动画格式，支持设置帧延迟和循环次数。APNG 格式兼容标准 PNG 解码器，同时为支持 APNG 的浏览器提供动画功能。

## 已编译版本

- 3.1.10 (2026-05-27)

## 特性

- 多帧 PNG 合成 APNG
- 帧延迟和循环设置
- 兼容标准 PNG 格式

## 使用方法

```bash
# 合成 APNG 动画
apngasm output.png frame1.png frame2.png frame3.png
```