# stk — Synthesis ToolKit in C++

STK 是一组开源 C++ 音频合成和处理类库，由 Gary Scavone 和 Perry Cook 开发，最初在 Princeton 大学创建。

## 简介

STK 提供：
- 物理建模合成算法（Clarinet、Flute、Brass、Sitar 等）
- 通用合成工具（ADSR、Envelope、Noise、SineWave 等）
- 音频效果处理（Chorus、Echo、Reverberation 等）
- 音频文件读写（FileRead、FileWrite、WvIn、WvOut）
- MIDI 文件输入（MidiFileIn）
- 实时音频 I/O（RtAudio/RtMidi，可选依赖 ALSA/PulseAudio/JACK）

## OpenHarmony 适配说明

在 OpenHarmony/HarmonyOS 平台：
- **必须使用 `--disable-realtime`**（鸿蒙平台无 ALSA/PulseAudio/JACK 音频库）
- **必须使用 `--enable-shared`**（默认只构建静态库，install 目标需要共享库）
- **必须设置 `RAWWAVE_PATH`** 为安装路径下 `share/stk/rawwaves`，否则运行时找不到波形数据
- **静态库需手动安装**（默认 `make install` 只安装共享库和头文件）
- demo/effects/ragamatic 项目依赖 realtime 音频功能，禁用后无法编译

## 编译版本

| 字段 | 值 |
|------|-----|
| 版本 | 5.0.1 |
| 状态 | published |
| 构建系统 | autotools |
| 编译器 | clang/clang++ (C++11) |
| 编译日期 | 2026-06-03 |

## 编译产物

| 文件 | 大小 | 说明 |
|------|------|------|
| libstk.a | 1.7MB (1738572 bytes) | 静态库（78个对象） |
| libstk-5.0.0.so | 633KB (633280 bytes) | 共享库 |
| libstk.so | symlink → libstk-5.0.0.so | 共享库 symlink |
| include/stk/*.h | 104 个文件 | 头文件 |
| share/stk/rawwaves/*.raw | 41 个文件 | 波形数据文件 |

## 依赖

- libm（系统数学库）
- libc++_shared.so（运行时依赖，共享库链接时）
- libc.so（运行时依赖，共享库链接时）

## 配置选项

```bash
./configure --prefix=$DEFAULT_PREFIX --disable-realtime --enable-shared \
    RAWWAVE_PATH=$DEFAULT_PREFIX/share/stk/rawwaves
```

## 补丁

1. `0001-config-config.guess.patch` — 更新平台识别支持 aarch64-unknown-linux-ohos
2. `0002-config-config.sub.patch` — 更新平台识别支持 aarch64-unknown-linux-ohos