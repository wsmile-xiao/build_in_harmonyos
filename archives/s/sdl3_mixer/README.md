# SDL3_mixer

SDL3_mixer 是一个音频混音库，用于 SDL3（Simple DirectMedia Layer 3）项目。

## 描述

SDL3_mixer 提供以下功能：
- 多种音频格式的解码支持（WAV、MP3、OGG、FLAC、MIDI 等）
- 多音轨混音功能
- 音频特效处理
- 空间音频支持
- 流式音频播放

## 版本信息

- 最新版本: 3.2.4
- 发布日期: 2024
- 官方网站: https://github.com/libsdl-org/SDL_mixer

## 依赖

- SDL3 (>= 3.0.0)

## 音频格式支持

- WAV、AIFF、AU、VOC（内置）
- MP3（使用 dr_mp3）
- FLAC（使用 dr_flac 或 libFLAC）
- OGG Vorbis（使用 stb_vorbis）
- MIDI（使用 Timidity）

## 构建系统

- CMake

## 许可证

zlib license

## 安装

可通过 cmd-pkgs 预编译包安装：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- sdl3_mixer 3.2.4
```

## 使用示例

参见归档中的示例程序：
- basics-load-and-play: 基本音频播放
- basics-play-with-options: 播放选项控制
- basics-play-multiple-sounds: 多音源播放