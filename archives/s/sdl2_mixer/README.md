# sdl2_mixer

## 简介
SDL_mixer —— 基于 SDL2 的多通道音频混音库，支持 WAV、MP3 等格式的播放与混音。

## OHOS 适配
- CMake 构建，静态库（BUILD_SHARED_LIBS=OFF）
- SDL2_mixer 自带 FindPrivateSDL2.cmake（模块模式）查 SDL2，
  配方 generate() 显式注入 SDL2_INCLUDE_DIR / SDL2_LIBRARY
- 裁剪非必要音频格式：OPUS/VORBIS/FLAC/MOD/MIDI/WAVPACK/GME/CMD=OFF，
  仅保留 WAV + MP3（内建 minimp3），消除外部编解码依赖
- E092：CMake 不识别 HarmonyOS 平台，用 CMAKE_SYSTEM_NAME=Linux 兼容
- 头文件装在 include/SDL2/，package_info() 显式声明 includedirs

## 依赖
- sdl2/2.30.10（ohpcd 制品仓）

## 功能验证
- test_package 编译链接 libSDL2_mixer.a，调用 Mix_Init/Mix_Quit API
  （OHOS ELF 签名后执行，exit=0）
- W3 本地 CI：conan create + test_package + L0-L5 门禁全 PASS

## 参考
- 上游: https://github.com/libsdl-org/SDL_mixer
