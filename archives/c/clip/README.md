# clip

clip 是一个命令行图像裁剪和调整大小工具，支持 PNG 和 JPEG 格式。

## 描述

clip 提供简单的命令行接口用于图像裁剪和尺寸调整，适合批处理和自动化图像处理工作流。它使用 libpng 和 libjpeg 进行图像读写。

## 已编译版本

- 0.7 (2026-05-27)

## OHOS 适配说明

- musl strerror_r 兼容性问题：musl 定义 `_GNU_SOURCE` 但 strerror_r 仍返回 `int`（POSIX 版）
- 修改 `#ifdef _GNU_SOURCE` → `#if defined(__GLIBC__)` 精确检测 glibc 环境

## 使用方法

```bash
# 裁剪图像
clip -crop 100x100+50+50 input.png output.png
```