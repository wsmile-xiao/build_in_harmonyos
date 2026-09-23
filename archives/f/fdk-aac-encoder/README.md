# fdk-aac-encoder (fdkaac)

fdk-aac-encoder 是 nu774 开发的 FDK-AAC 命令行编码器前端（上游二进制名 `fdkaac`），
封装 Fraunhofer FDK-AAC 编解码库，将 WAV/CAF/raw PCM 编码为 AAC 音频：

- Profile：MPEG-4 AAC-LC / HE-AAC (SBR) / HE-AACv2 (SBR+PS) / AAC-LD / AAC-ELD
- CBR（--bitrate）与 VBR（--bitrate-mode 1-5）
- 容器：M4A（默认，含 iTunes 风格标签 iTunSMPB/gapless 元数据）、ADIF/ADTS/LATM/LOAS
- smart-padding（LPC pre/post-roll）实现样本级 gapless 播放边界
- 多种输入格式：WAV（含 32bit float）、CAF、raw PCM（--raw-*）

> 上游官方源为 GitHub 仓库 https://github.com/nu774/fdkaac（COPYING Source 字段）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.0.9 | published | 首次适配（CMake 构建，零补丁） |

## 依赖

- fdk-aac/2.0.3（Fraunhofer FDK-AAC 编解码库）
- libsndfile/1.2.2（音频工具链同族依赖）

## 用法（安装后）

```bash
fdkaac -b 128000 -o output.m4a input.wav
fdkaac --help    # 版本与全部选项
```
