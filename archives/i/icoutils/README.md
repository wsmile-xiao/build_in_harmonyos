# icoutils

icoutils 是一组用于提取和转换 Windows 图标和光标资源的工具。

## 描述

icoutils 包含 icotool（提取/创建 ICO 文件）和 wrestool（从 Windows PE 可执行文件中提取资源）。它还包含 extresso 和 genresscript 用于自动化资源提取，是跨平台应用开发的常用工具。

## 已编译版本

- 0.32.3 (2026-05-27)

## 依赖

- libpng (PNG 图像读写)

## OHOS 适配说明

- libpng.so 符号链接需要手动创建（libpng.so → libpng16.so）
- CFLAGS 简化避免 clang 15 不支持的警告标志

## 使用方法

```bash
# 从 ICO 文件提取图标
icotool -x icons.ico

# 从可执行文件提取资源
wrestool -x application.exe
```