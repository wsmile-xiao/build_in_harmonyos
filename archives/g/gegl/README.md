# GEGL

GEGL (Generic Graphics Library) 是一个基于图的图像处理框架，为 GIMP 和其他图形应用提供图像处理操作管线。

## 描述

GEGL 提供基于节点图的图像处理管线架构，支持链式操作组合。它是 GIMP 2.10+ 的核心引擎，也被其他图像处理工具使用。GEGL 支持大图像的按需缓存处理，避免内存溢出。

## 已编译版本

- 0.4.70 (2026-05-27)
- 0.4.71 (2026-05-27)

## 依赖

- babl (颜色空间转换)
- glib (基础库)
- libpng

## OHOS 适配说明

- meson 构建系统，1 patch for meson.build 平台适配
- check-def-files 验证步骤在 HarmonyOS 平台需跳过（libintl/gnulib 符号泄漏）
- 多个可选依赖已禁用以简化构建

## 使用方法

```bash
# 简单图像处理
gegl input.png -- output.png
```