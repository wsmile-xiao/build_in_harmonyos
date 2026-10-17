# OpenSlide

## 简介
OpenSlide 是用于读取数字病理全幻灯片图像（Whole-Slide Images）的 C 语言库，提供统一的多级金字塔图像访问 API，支持 TIFF、JPEG、JPEG 2000、PNG、DICOM 及多种厂商格式。

## OHOS 适配
- 上游版本：4.0.1
- 构建系统：Meson
- 目标平台：HarmonyOS PC AArch64
- 依赖通过 Conan 注入，并通过生成的 pkg-config 文件供 Meson 探测
- 附带 `slidetool` 命令行工具

## 参考
- 上游仓库：https://github.com/openslide/openslide
- 官网：https://openslide.org/
