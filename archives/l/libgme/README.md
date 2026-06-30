# libgme

## 简介

libgme（Game Music Emu）是一个视频游戏音乐模拟库，可以播放来自 NES、Game Boy、Sega Genesis/Mega Drive、PC Engine、Sega Master System 等经典游戏机的音乐格式。

## 支持的音乐格式

- AY (ZX Spectrum)
- GBS (Game Boy)
- GYM (Sega Genesis/Mega Drive)
- HES (PC Engine/TurboGrafx-16)
- KSS (MSX Home Computer)
- NSF (NES/Famicom)
- NSFE (NES/Famicom with extended info)
- SAP (Atari computers)
- SPC (Super NES/Super Famicom)
- VGM (Sega Master System/Genesis/Mega Drive)
- VGZ (VGM compressed)

## OHOS 适配

### 适配要点

1. **CMake 构建系统**：使用 CMake 构建，无需特殊补丁
2. **平台检测**：CMake 会警告未知平台 HarmonyOS，但不影响编译
3. **编译器**：使用 clang/clang++ 编译通过

### 已知问题

1. **编译警告**：部分 C++ 文件缺少 `override` 关键字，不影响功能
2. **SDL2 未找到**：SDL2 是可选依赖，用于构建 demo player，不影响核心库

### 与 Linux 的差异

无明显差异，标准 CMake 构建流程即可完成编译。

## 依赖

### 编译依赖
- CMake >= 3.14
- clang/clang++
- zlib（系统自带）

### 可选依赖
- SDL2（用于 demo player，非必需）

## 功能验证

libgme 是一个纯库，没有独立的可执行文件。验证方式：

```c
#include <gme/gme.h>
#include <stdio.h>

int main() {
    printf("libgme version: %s\n", gme_version);
    return 0;
}
```

编译：
```bash
clang -o test_gme test_gme.c -lgme
./test_gme
```

## 参考

- 官方 Wiki: https://bitbucket.org/mpyne/game-music-emu/wiki/Home
- 源码仓库: https://bitbucket.org/mpyne/game-music-emu