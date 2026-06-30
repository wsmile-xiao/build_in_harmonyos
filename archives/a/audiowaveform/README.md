# audiowaveform

audiowaveform 是一个从音频文件生成波形图和 JSON 数据的工具，用于 BBC 音频波形可视化项目。

## 描述

audiowaveform 可以从音频文件生成 PNG/SVG 波形图和 JSON 波形数据，用于 Web 音频播放器的波形可视化。它支持多种音频格式输入，输出分辨率和样式可调。

## 已编译版本

- 1.10.3 (2026-05-27)

## 依赖

- libgd (图像渲染)
- libpng
- libjpeg-turbo

## OHOS 适配说明

- CMakeLists.txt 补丁修复 libgd.a 传递依赖缺失问题

## 使用方法

```bash
# 生成波形 PNG 图像
audiowaveform -i input.mp3 -o waveform.png
```