# SoundTouch — 开源音频变速变调 DSP 库

[SoundTouch](https://www.surina.net/soundtouch/) 是一个开源音频处理库，
基于 WSOLA 算法实现音频的节奏(Tempo)、音高(Pitch)与播放速率(Rate)的
独立调整。附带 soundstretch 命令行工具处理 WAV 文件。

- 上游主仓：https://gitlab.com/soundtouch/soundtouch
- 许可证：LGPL-2.1-or-later
- 语言：C++（零第三方依赖，仅 libm）

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 2.0.0 | published | 2017-07 发布；纯 autotools 构建（CMake 支持 2.1.0 起才有） |
