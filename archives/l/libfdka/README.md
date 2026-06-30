# libfdka

## 简介

libfdka（fdk-aac）是 Fraunhofer FDK AAC 编解码库，提供高质量的 AAC（Advanced Audio Coding）音频编解码功能。该库被广泛用于多媒体应用中，支持 AAC-LC、HE-AAC、HE-AACv2 等多种 AAC 格式。

## 版本信息

- **当前版本**: 2.0.2
- **上游源码**: https://github.com/mstorsjo/fdk-aac
- **许可证**: 自定义许可（非自由软件，但允许特定用途）

## 功能特性

- AAC 编码和解码
- 支持 AAC-LC、HE-AAC、HE-AACv2、USAC
- 高质量音频处理
- 支持 DRC（动态范围控制）
- 支持 SBR（频带复制）
- 支持 PS（参数立体声）

## 编译说明

本软件使用 CMake 构建系统编译，编译过程如下：

```bash
cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
      -DCMAKE_BUILD_TYPE=Release \
      ..
make -j$(nproc)
make install DESTDIR=/storage/Users/currentUser/test-install-libfdka-2.0.2
```

### 编译依赖

- C++ 编译器（clang/gcc）
- CMake 3.10+

### 平台适配

在 OpenHarmony 平台上编译时，CMake 会识别为未知平台（HarmonyOS），但不影响编译过程。无需特殊补丁。

## 安装产物

编译成功后生成的产物：

- **库文件**: `libfdk-aac.so`（共享库）
- **头文件**: `fdk-aac/*.h`（API 头文件）
- **pkg-config**: `fdk-aac.pc`（包配置文件）

## 使用示例

```c
#include <aacdecoder_lib.h>
#include <aacenc_lib.h>

// 解码示例
HANDLE_AACDECODER decoder = aacDecoder_Open(TT_MP4_ADTS, 1);
aacDecoder_DecodeFrame(decoder, pcmBuffer, bufferSize);
aacDecoder_Close(decoder);

// 编码示例
HANDLE_AACENCODER encoder = aacEnc_Open(&encInfo, 0);
aacEnc_SetParam(encoder, AACENC_BITRATE, 128000);
aacEnc_Encode(encoder, inBuffer, inSize, outBuffer, outSize);
aacEnc_Close(&encoder);
```

## 注意事项

- fdk-aac 的许可证允许用于商业用途，但不允许修改后分发
- 该库被 ffmpeg 等多媒体框架广泛使用
- 性能优化需要根据具体应用场景调整编码参数

## 已编译版本

- 2.0.2（2026-05-22）

## 参考链接

- [上游仓库](https://github.com/mstorsjo/fdk-aac)
- [AAC 编解码技术文档](https://en.wikipedia.org/wiki/Advanced_Audio_Coding)