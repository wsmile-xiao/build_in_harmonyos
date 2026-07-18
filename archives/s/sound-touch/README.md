# SoundTouch — 音频处理库

SoundTouch 是一个开源音频处理库，用于独立调整音频流或音频文件的节奏(Tempo)、音高(Pitch)和播放速率(Playback Rates)。

## 功能概述

- **Tempo 变换**：改变播放速度而不改变音高
- **Pitch 变换**：改变音高而不改变播放速度
- **Rate 变换**：同时改变播放速度和音高
- **SoundStretch 命令行工具**：基于 SoundTouch 库的命令行音频处理工具

## 上游信息

- **上游仓库**: https://codeberg.org/soundtouch/soundtouch
- **Homebrew 公式**: https://github.com/Homebrew/homebrew-core/blob/master/Formula/s/sound-touch.rb
- **许可证**: LGPL-2.1-or-later

## OHOS 适配要点

- **Bootstrap 前置步骤**：源码包不含 configure 脚本，需先运行 `./bootstrap` (autoreconf)
- **HMDFS umask 修复**：autoreconf 生成的 configure 包含 `umask 077`，需替换为 `umask 022`
- **clang_rt.builtins 链接**：OHOS aarch64 需链接 `-lclang_rt.builtins` 解决 `__powidf2` 符号
- **NEON 禁用**：配置时需添加 `--disable-neon-optimizations`

## 版本列表

| 版本 | 状态 | 构建日期 | 说明 |
|------|------|----------|------|
| homebrew | built | 2026-07-17 | Homebrew 公式版本 (上游 2.4.1) |
| 2.4.0 | published | 2026-06-06 | 上游版本 2.4.0 |
