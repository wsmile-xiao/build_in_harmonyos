# SoX - Sound eXchange

## 简介

SoX（Sound eXchange）是一个通用的音频处理工具，被誉为"音频领域的瑞士军刀"。它可以读取和写入多种音频格式文件，应用各种音频效果，并能在不同格式之间进行转换。

## 功能特点

- **音频格式转换**：支持 20+ 种音频格式，包括 WAV, MP3, FLAC, OGG, AIFF 等
- **音频效果处理**：提供丰富的音频效果，如音量调整、回声、混响、降噪等
- **音频播放**：可以播放多种格式的音频文件
- **音频录制**：可以录制音频并保存为指定格式
- **批量处理**：支持脚本化批量处理音频文件

## 支持的音频格式

- **输入格式**：WAV, AIFF, AU, RAW, FLAC, OGG, MP3, AAC, WMA 等
- **输出格式**：支持所有输入格式以及更多编码格式

## 编译说明

### 构建系统

- **类型**：Autotools (configure + make)
- **依赖**：可选多种音频库依赖，最小编译仅需基本构建工具

### 编译选项

SoX 支持大量可选依赖，可以根据需要启用：
- `--with-lame`：启用 MP3 编码支持
- `--with-flac`：启用 FLAC 支持
- `--with-oggvorbis`：启用 OGG Vorbis 支持
- 更多选项请查看 `./configure --help`

### OHOS 适配

在 OpenHarmony 平台编译时需要注意：
- 需要正确配置 config.guess 和 config.sub
- 需要处理可选依赖的缺失情况
- 需要确保生成的二进制已签名

## 许可证

- **主许可证**：GPL-2.0+（大部分代码）
- **库许可证**：LGPL-2.1+（libsox 库）

## 官网

- 主页：https://sox.sourceforge.net/
- 源码：https://sourceforge.net/projects/sox/

## 版本信息

- 当前编译版本：14.4.2
- 发布日期：2015-02-22