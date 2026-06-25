# pcaudiolib

Portable C Audio Library - 提供跨平台的音频输出接口。

## 描述
pcaudiolib 是一个轻量级的 C 语言音频库，支持多种音频后端：
- OSS (Open Sound System)
- ALSA (Advanced Linux Sound Architecture)
- PulseAudio
- QSA (QNX Sound Architecture)
- CoreAudio (Mac OS)

## 已编译版本
- 1.3 (2026-05-19)

## 使用方法
```c
#include <pcaudiolib/audio.h>

int main() {
    audio_object *audio = create_audio_object("device", "app");
    // 使用 audio API
    destroy_audio_object(audio);
    return 0;
}
```

## 依赖
- 无强依赖
- OSS 支持：sys/soundcard.h

## 许可证
GPL v3+
