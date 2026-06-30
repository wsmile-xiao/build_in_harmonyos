# ffmpeg-full — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf ffmpeg-full-8.1.1-ohos-aarch64.tar.gz -C ~/usr/local

cd ffmpeg-full-8.1.1-ohos-aarch64 && sh install-ffmpeg-full-8.1.1.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 8.1.1 | published | 1 |

## 当前版本 (8.1.1) 详情

### 包内容
- 二进制: ffmpeg, ffprobe, ffplay
- 共享库: libavcodec, libavformat, libavfilter, libavdevice, libswscale, libswresample, libavutil
- 包大小: 286MB (release), 143MB (debug)

### 编译信息
- 构建系统: custom-configure
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 1

### 补丁列表
- 0001-configure-add-harmonyos-os-detection.patch

### 启用的编解码库
- libfreetype (字体渲染)
- libharfbuzz (文本塑形)
- libfribidi (双向文本)
- libopus (Opus音频)
- libvorbis (Vorbis音频)
- libtheora (Theora视频)
- libopenjpeg (JPEG 2000)
- libmp3lame (MP3编码)
- libsoxr (音频重采样)
- openssl (TLS支持)

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- 需要以上编解码库的预编译包已安装