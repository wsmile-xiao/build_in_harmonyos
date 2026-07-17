# blind

blind 是 suckless.org 出品的一组 Unix 命令行视频处理工具。

## 描述

blind 提供了一系列命令行工具用于视频流处理，支持色彩转换、几何变换、时间操作等。所有工具以管道方式协作，遵循 Unix 设计哲学。

## 已编译版本

- 1.1 (2026-07-15)

## 特性

- 命令行视频管道处理
- 色彩空间转换（CIE XYZ、sRGB）
- 几何变换（裁剪、翻转、缩放）
- 时间操作（拼接、裁剪帧）

## 使用方法

```bash
# 从图像生成视频帧
blind-from-image input.png | blind-to-video output.mp4
```
