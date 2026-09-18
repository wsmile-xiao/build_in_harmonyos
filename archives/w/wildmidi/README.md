# wildmidi

**WildMIDI** - 软件 MIDI 合成器库（libWildMidi）

WildMIDI 将标准 MIDI 文件实时合成为 PCM 音频样本，支持 GUS patch 音色库。
本包在 OHOS 上以纯库形态提供（上游可选的 wildmidi 播放器依赖 ALSA/OSS/OpenAL
音频后端，OHOS 均不具备，故按上游 CMake 开关禁用）。

## 公开 API（include/wildmidi_lib.h）

| 函数 | 说明 |
|------|------|
| WildMidi_Init | 初始化合成器（读取 wildmidi.cfg 配置） |
| WildMidi_Open / WildMidi_OpenBuffer | 打开 MIDI 文件/内存缓冲 |
| WildMidi_GetOutput / WildMidi_ConvertBufferToWav | 取合成输出 |
| WildMidi_SetOption / WildMidi_SetCvtOption | 设置播放/转换选项 |
| WildMidi_Close / WildMidi_Shutdown | 关闭句柄/关闭库 |
| WildMidi_GetError / WildMidi_ClearError | 错误信息读取/清除 |

上游文档：https://github.com/Mindwerks/wildmidi/wiki
