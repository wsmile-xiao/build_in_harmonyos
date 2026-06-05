# Chromaprint

## 简介

Chromaprint 是一个音频指纹库，专为 [AcoustID](https://acoustid.org/) 项目开发。它设计用于识别近似相同的音频内容，生成的指纹尽可能紧凑。它不是一个通用音频指纹解决方案，而是为了搜索性能而牺牲精度和鲁棒性。

**主要用途**：
- 全音频文件识别
- 重复音频文件检测
- 长音频流监控

**官网**：https://acoustid.org/chromaprint  
**GitHub**：https://github.com/acoustid/chromaprint

## 依赖

- FFT 库（可选 KissFFT、FFTW3、FFmpeg、vDSP）
- FFmpeg/libswresample（可选，用于音频解码和格式转换）
- 系统库：libc++_shared.so, libc.so

## 编译选项

本项目支持以下编译配置：
- `FFT_LIB`: 选择 FFT 实现（kissfft, fftw3, avfft 等）
- `USE_INTERNAL_AVRESAMPLE`: 使用内置 avresample 进行音频格式转换
- `BUILD_SHARED_LIBS`: 构建共享库
- `BUILD_TOOLS`: 构建 fpcalc 工具（需要 FFmpeg）
- `BUILD_TESTS`: 构建测试套件（需要 Google Test）

## 预编译包信息

- **最新版本**：1.6.0
- **平台**：OpenHarmony aarch64
- **构建系统**：CMake
- **FFT 库**：内置 KissFFT
- **音频转换**：内置 avresample

## 安装方式

```bash
# 通过 cmd-pkgs 公共安装脚本安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- chromaprint 1.6.0
```

## 使用示例

```c
#include <chromaprint.h>

chromaprint_ctx_t ctx;
chromaprint_new(&ctx);
chromaprint_start(ctx, 44100, 1);
// ... 处理音频数据 ...
chromaprint_finish(ctx);
char *fingerprint;
chromaprint_get_fingerprint(ctx, &fingerprint);
// 使用指纹进行音频识别
chromaprint_free_string(fingerprint);
chromaprint_free(ctx);
```

## 版本历史

| 版本 | 发布日期 | 说明 |
|------|---------|------|
| 1.6.0 | 2024-08 | 支持 FFmpeg 8.0，优化性能，CMake 改进 |
| 1.5.1 | 2021-09 | macOS fat binaries 支持 |
| 1.5.0 | 2020-03 | 新增 libavresample 支持，bug 修复 |

## 相关链接

- [AcoustID 项目](https://acoustid.org/)
- [Chromaprint GitHub](https://github.com/acoustid/chromaprint)
- [API 文档](https://acoustid.org/chromaprint)