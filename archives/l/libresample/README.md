# libresample

## 软件简介

libresample 是一个实时音频重采样库，由 Dominic Mazzoni 开发，基于 Julius Smith 的 resample-1.7 库。

- **功能**: 提供高质量的音频采样率转换功能
- **许可证**: BSD 或 LGPL（可选择）
- **项目地址**: https://github.com/minorninth/libresample

## 编译状态

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| 0.1.5 | built | 2026-06-11 | HMDFS 限制，使用预配置文件 |

## 特性

- 实时采样率转换
- 单精度浮点运算
- 便携性好
- BSD/LGPL 双许可证

## 相关库

- **libsamplerate**: Erik de Castro Lopo 开发的高质量重采样库（GPL 许可证）
- **libresample**: 本库（BSD/LGPL 许可证，更自由）

## 注意事项

本软件在 OpenHarmony/HMDFS 文件系统上编译时，configure 脚本无法正常工作。需要使用预配置的 Makefile 和 config.h 文件（位于 hints 目录）。