# opus

高质量音频编解码库，支持语音和音乐，低延迟、高保真。

## 版本
- 1.4 (2026-05-19)

## 特点
- 低延迟（5-66.5ms）
- 高保真音频
- 自适应比特率
- WebRTC/VoIP 标准

## 库文件
- libopus.a (2.3 MB) - 静态库（推荐）
- libopus.so (1.2 MB) - 动态库

## 头文件
- opus.h, opus_defines.h, opus_types.h
- opus_multistream.h, opus_projection.h

## 安装
curl install.sh | sh -s -- opus 1.4

## 验证
```c
#include <opus/opus.h>
printf("%s\n", opus_get_version_string());
```

## 注意
推荐使用静态库链接，避免动态库加载问题。
