# opus-tools

opus-tools 是 Opus 音频编解码器的命令行工具集，包含编码器 (opusenc)、解码器 (opusdec) 和信息查看器 (opusinfo)。

## 描述

opus-tools 提供了一组用于处理 Opus 音频格式的命令行工具，支持 WAV/FLAC 到 Opus 的编码以及 Opus 到 WAV 的解码。

## 已编译版本
- 0.2 (2026-05-26)

## 依赖
- opus 1.4
- libogg 1.3.6
- opusfile 0.12
- libopusenc 0.2.1
- flac 1.4.3

## 特性
- Opus 音频编码 (opusenc)
- Opus 音频解码 (opusdec)
- Opus 文件信息查看 (opusinfo)
- 支持 WAV、FLAC 输入格式
- 支持 Opus 输出格式

## 使用方法
```bash
# 编码 WAV 到 Opus
opusenc input.wav output.opus

# 编码 FLAC 到 Opus
opusenc input.flac output.opus

# 解码 Opus 到 WAV
opusdec input.opus output.wav

# 查看 Opus 文件信息
opusinfo file.opus
```

## 注意事项
- opusurl(HTTP URL streaming)在 HarmonyOS 上不可用，opusdec 不支持直接从 URL 读取
- 编译时需手动修正部分 cmd-pkgs 依赖包的安装路径