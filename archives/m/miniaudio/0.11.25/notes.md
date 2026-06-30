# miniaudio 0.11.25 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 使用 `ohc-run.py init-build miniaudio 0.11.25 --url=https://github.com/mackron/miniaudio/archive/refs/tags/0.11.25.tar.gz` 初始化
2. 使用 CMake 构建，禁用所有非 null 音频后端：
   ```bash
   cd miniaudio-0.11.25.work/build
   cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
     -DMINIAUDIO_BUILD_EXAMPLES=OFF \
     -DMINIAUDIO_BUILD_TESTS=OFF \
     -DMINIAUDIO_BUILD_TOOLS=OFF \
     -DMINIAUDIO_NO_ALSA=ON \
     -DMINIAUDIO_NO_PULSEAUDIO=ON \
     -DMINIAUDIO_NO_JACK=ON \
     -DMINIAUDIO_NO_SNDIO=ON \
     -DMINIAUDIO_NO_OSS=ON \
     -DMINIAUDIO_NO_AAUDIO=ON \
     -DMINIAUDIO_NO_OPENSL=ON \
     -DMINIAUDIO_NO_COREAUDIO=ON \
     -DMINIAUDIO_NO_DSOUND=ON \
     -DMINIAUDIO_NO_WASAPI=ON \
     -DMINIAUDIO_NO_WINMM=ON \
     -DMINIAUDIO_NO_AUDIO4=ON \
     -DMINIAUDIO_NO_WEBAUDIO=ON \
     -DMINIAUDIO_NO_CUSTOM=ON
   make -j2
   ```
3. DESTDIR 安装：`make install DESTDIR=$TEST_PREFIX`
4. 编写测试程序验证 API 功能（ma_context_init, device enumeration）
5. 打包并收尾

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 无 ALSA/PulseAudio/JACK 等音频后端 | OHOS 平台不支持 Linux 传统音频子系统 | 使用 CMake 选项禁用所有真实后端（MINIAUDIO_NO_*），仅保留 null 后端 |
| 2 | CMake 检测 OHOS 为未知系统 | CMake 没有 HarmonyOS 平台定义 | CMake 虽报 warning 但仍可正常构建 |
| 3 | vorbisfile 链接失败 | pkg-config 找不到 vorbisfile.pc | 测试时使用 MA_NO_LIBVORBIS 禁用 vorbis 依赖 |

## 源码修改

无源码修改。miniaudio 是 header-only 库，所有适配通过 CMake 配置选项完成，无需补丁。

## 依赖版本

- vorbisfile 1.3.7 (静态库已安装，pkg-config 不可用)

## 验证结果

```bash
# Header-only 编译验证
clang -DMA_NO_* ... test_miniaudio_api.c -lm -lpthread
→ ALL TESTS PASSED: ma_context_init, version 0.11.25, device enumeration, uninit

# 链接静态库验证
clang ... examples/simple_enumeration.c -lminiaudio -lm -lpthread
→ Playback Devices: NULL Playback Device
→ Capture Devices: NULL Capture Device
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| miniaudio.h | 4.1MB | 主头文件 |
| libminiaudio.a | 913KB | 静态库（含 null 后端实现） |
| miniaudio.pc | pkg-config | 包含所有 MA_NO_* 编译标志 |

## 注意事项

- miniaudio 是单头文件库（header-only），核心使用方式是 `#define MINIAUDIO_IMPLEMENTATION` + `#include "miniaudio.h"`
- 在 OHOS 上仅 null 后端可用，无实际音频播放/捕获功能
- 编译时需要禁用所有不可用的音频后端以避免链接错误
- vorbisfile 在 OHOS 上作为静态库可用但 pkg-config 配置不完整
---

**编译结束**: 2026-05-29 10:52
**最终状态**: built
