# Rubber Band Library - 音频时间拉伸和音高移动库

## 简介

Rubber Band Library 是一个高质量的音频时间拉伸和音高移动库，提供 C++ 和 C API。由 Breakfast Quay 开发，广泛应用于音频处理软件中。

**官方网站**: https://breakfastquay.com/rubberband/

## 功能特性

- **时间拉伸**: 改变音频速度而不影响音高
- **音高移动**: 改变音频音高而不影响速度
- **高质量算法**: 提供多种拉伸模式（更快、更精细）
- **跨平台**: 支持多种操作系统和架构
- **多种接口**: C++ 类接口和 C 函数接口

## 版本历史

### 3.3.0 (当前版本)

- **构建系统**: meson + ninja
- **编译日期**: 2026-05-22
- **编译器**: clang 15.0.4
- **状态**: built
- **质量门禁**: G1-G4 全通过

**关键发现**:
- meson 构建需要设置 `PATH=/usr/bin:/bin:/usr/local/bin`
- HMDFS 软链接限制（非阻塞问题）

## 使用方法

### C++ API

```cpp
#include <rubberband/RubberBandStretcher.h>

using namespace RubberBand;

RubberBandStretcher stretcher(sampleRate, channels,
                              RubberBandStretcher::DefaultOptions,
                              1.0, 1.0);
stretcher.study(inputData, numSamples, true);
stretcher.process(inputData, numSamples, false);
stretcher.retrieve(outputData, available);
```

### C API

```c
#include <rubberband/rubberband-c.h>

RubberBandState state = rubberband_new(sampleRate, channels,
                                       RubberBandOptionProcessRealTime,
                                       1.0, 1.0);
rubberband_process(state, inputData, numSamples, false);
rubberband_available(state);
rubberband_retrieve(state, outputData, available);
rubberband_delete(state);
```

### pkg-config 集成

```bash
# 编译选项
pkg-config --cflags rubberband

# 链接选项
pkg-config --libs rubberband

# 版本查询
pkg-config --modversion rubberband  # 输出: 3.3.0
```

## 库文件

- **动态库**: librubberband.so.2.3.0 (458K)
- **静态库**: librubberband.a (793K)
- **头文件**:
  - RubberBandStretcher.h (C++ API)
  - rubberband-c.h (C API)
- **元数据**: rubberband.pc (pkg-config)

## 相关链接

- **官方网站**: https://breakfastquay.com/rubberband/
- **GitHub**: https://github.com/breakfastquay/rubberband
- **API文档**: https://breakfastquay.com/rubberband/code-doc/
- **GitCode归档**: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos_4044/tree/main/archives/r/rubberband