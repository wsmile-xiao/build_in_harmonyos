# EasyTAG

> Audio file metadata (tag) editor for GTK+

## 简介

EasyTAG 是一个用于查看和编辑音频文件元数据（标签）的工具，支持 MP3、FLAC、Ogg Vorbis、AAC 等多种格式。它基于 GTK+ 图形界面，方便批量编辑音频文件的标签信息。

## OHOS 适配要点

- 需要替换 config.guess/config.sub 以识别 OpenHarmony 平台
- GTK+ 和相关库的依赖可能需要通过预编译包安装

## 依赖

| 依赖 | 说明 |
|------|------|
| GTK+ 3 | 图形界面库 |
| id3lib | ID3 标签库 |
| libflac | FLAC 格式库 |
| libvorbis | Ogg Vorbis 库 |
| opus | Opus 音频编解码库 |

## 参考

- [官方主页](https://easytag.sourceforge.net/)
- [源码仓库](https://github.com/AmauryP/EasyTAG)