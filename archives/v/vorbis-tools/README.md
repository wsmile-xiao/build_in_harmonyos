# vorbis-tools

Vorbis 音频编码和解码工具集。

## 描述

vorbis-tools 是 Ogg Vorbis 音频格式的命令行工具集，包含：
- `oggenc`: Vorbis 音频编码器
- `oggdec`: Vorbis 音频解码器
- `ogginfo`: Ogg 文件信息查看器
- `vcut`: Ogg Vorbis 文件切割工具
- `vorbiscomment`: Vorbis 注释编辑器

## 官网

https://xiph.org/vorbis/

## 许可证

GPL-2.0

## 分类

audio-media

## 构建系统

autotools

## OHOS 适配

所有版本需要以下平台识别补丁：
- config.guess: 添加 HarmonyOS 平台识别
- config.sub: 接受 linux-ohos 作为合法 OS

## 版本索引

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.4.2 | built | 2026-06-03 | 最新稳定版本，完整适配 |