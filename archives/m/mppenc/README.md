# mppenc

Musepack (MPC) SV7 无损音频编码器命令行工具（mppenc）。

- 上游主页：https://www.musepack.net/
- 许可：LGPL-2.1-or-later
- 构建系统：CMake（c 语言，零外部依赖，仅链接 libm）
- 产物：`bin/mppenc`

用法：`mppenc [--quality N] input.wav output.mpc`（输入支持 32/37.8/44.1/48 kHz PCM WAV）
