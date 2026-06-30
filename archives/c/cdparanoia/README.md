# cdparanoia

cdparanoia 是一个带纠错功能的 CD 音频提取（ripping）库和命令行工具。

## 描述

cdparanoia（Paranoia III）是 Xiph.org 出品的 CD 音频提取工具，它通过高级纠错和抖动补偿技术确保从 CD 读取的数据完整无误。它是许多音频软件的基础依赖。

## 已编译版本

- 10.2 (2026-05-30)

## 特性

- CD 音频提取（ripping）
- 纠错和抖动补偿
- 共享库和静态库
- 命令行工具

## 使用方法

```bash
# 提取 CD 音轨到 WAV
cdparanoia -B
```