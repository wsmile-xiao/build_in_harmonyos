# TiMidity++

TiMidity++ 是一个软件合成器，可以将 MIDI 文件转换为 PCM 波形数据。它可以在没有外部 MIDI 乐器的情况下播放 MIDI 文件，并将生成的波形保存为各种音频文件格式。

## 基本信息

- **软件名称**: TiMidity++
- **版本**: 2.13.2
- **许可证**: GPL-2.0
- **官方网站**: http://www.timidity.jp
- **源码仓库**: https://sourceforge.net/projects/timidity/ (SourceForge 官方源)

## 功能特性

- 播放 MIDI 文件（无需外部 MIDI 乐器）
- 支持多种格式：SMF, MOD, RCP, MFi
- 转换为多种音频格式：WAV, AU, AIFF, Ogg Vorbis, FLAC
- 使用多种数字乐器数据：Gravis Ultrasound patch, SoundFonts, AIFF/WAV

## HarmonyOS 平台编译说明

### 编译状态
- **版本**: 2.13.2
- **状态**: 已编译成功 (built)
- **编译日期**: 2026-06-05
- **架构**: aarch64

### 平台适配问题

本软件在 HarmonyOS 平台编译时遇到以下问题：

1. **平台识别问题 (E007)**:
   - config.guess 无法识别 HarmonyOS 系统
   - 解决方案：修改 config.guess 和 config.sub 添加 HarmonyOS 支持

2. **HMDFS 权限限制**:
   - HMDFS 文件系统的 SELinux 权限限制导致 autotools 无法创建临时文件
   - 解决方案：在 `/data/storage/el2/base/cache` 目录下编译

### 编译配置

由于 HarmonyOS 平台缺少音频驱动支持，本次编译配置为：
- 禁用音频播放功能 (`--enable-audio=no`)
- 禁用所有图形界面
- 仅保留命令行功能

主要用途：作为 MIDI 到 WAV 的转换工具。

### 依赖项

- libc.so (musl)
- 无其他外部库依赖

### 安装方式

#### 使用预编译包安装

下载预编译包后，解压并安装：

```bash
tar xzf timidity-2.13.2-ohos-aarch64.tar.gz
# 将 bin/ 和 man/ 目录移动到目标位置
mv bin /path/to/install/bin/
mv man /path/to/install/man/

# 重新签名（首次安装需要）
/data/service/hnp/bin/sign-elf /path/to/install/bin/timidity
```

#### 验证安装

```bash
timidity --version
# 输出: TiMidity++ version 2.13.2
```

### 使用示例

#### 将 MIDI 文件转换为 WAV

```bash
timidity input.mid -Ow -o output.wav
```

#### 转换为其他格式

```bash
# AU 格式
timidity input.mid -Ou -o output.au

# AIFF 格式
timidity input.mid -Oa -o output.aiff
```

### 配置说明

TiMidity++ 需要 `timidity.cfg` 配置文件和音色库才能播放 MIDI。

默认配置文件路径：`$PREFIX/share/timidity/timidity.cfg`

首次使用时需要：
1. 创建配置文件目录
2. 配置音色库路径（如 SoundFont 文件）

## 归档文件

- **编译版本归档**: `archives/t/timidity/2.13.2/`
  - manifest.yaml: 编译元数据
  - notes.md: 编译笔记
  - patches/: 平台适配补丁
  - packaging/: 预编译包
  - reports/: 编译报告（configure.log, make.log 等）

## 补丁文件

- `0001-config.guess-harmonyos.patch`: 添加 HarmonyOS 平台识别
- `0002-config.sub-harmonyos.patch`: 添加 HarmonyOS 系统支持
- `0003-configure-hmdfs-umask.patch`: 修复 HMDFS 文件系统 umask 权限问题

## 相关链接

- [TiMidity++ 官方文档](http://timidity.sourceforge.net)
- [编译笔记](archives/t/timidity/2.13.2/notes.md)
- [编译元数据](archives/t/timidity/2.13.2/manifest.yaml)