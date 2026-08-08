# milkytracker

MilkyTracker — 受 Fast Tracker 2 启发的跨平台音乐制作工具（MOD/XM tracker），GPLv3。

## 简介

milkytracker 是一个开源、跨平台的音乐创作应用，用于创作 .MOD 和 .XM 模块文件。
它复刻了 DOS 时代 FastTracker II 的模块回放体验与操作方式，并提供改进的
Amiga ProTracker 2/3 兼容播放模式。项目附带命令行工具 milkycli，
可将 .xm 模块离线导出为 WAV 音频。

本适配面向 OpenHarmony PC（aarch64）。

## 主要组件

- **milkytracker**: SDL2 图形界面的 tracker 主程序
- **milkycli**: 命令行工具，将 .xm 模块导出为 WAV（无显示环境可运行，用于功能验证）
- **milky.xm 等示例曲目**: 安装到 `share/milkytracker/songs/`

## OpenHarmony 编译说明

- 构建系统：CMake（`cmake_minimum_required(3.10)`，C++11）
- 依赖：sdl2/2.30.10（cnb 制品仓静态包）
- 关键适配点：
  - `CMAKE_SYSTEM_NAME=Linux`（E092：CMake 不识别 HarmonyOS 平台）
  - CMP0004 加版本守卫（CMake 4.x 不再允许 OLD 行为）
  - Synths.cpp 三元表达式补显式强转（clang15 C++11 严格模式 narrowing 报错）
  - OHOS ELF 签名（binary-sign-tool），否则运行报 Operation not permitted
- 可选依赖（zlib/lhasa/zziplib/ALSA/JACK/RtMidi）缺失时对应功能自动禁用

## 许可证

GPL-3.0-or-later

## 主页

https://milkytracker.titandemo.org/

## 版本历史

| 版本 | 日期 | 状态 | 备注 |
|------|------|------|------|
| 1.06 | 2026-08-07 | published | aarch64 构建，SDL2 静态链接，2 个平台适配补丁 |
