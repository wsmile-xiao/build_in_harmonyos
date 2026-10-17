# librubberband - 音频时间拉伸和音高移动库

## 简介

Rubber Band Library 是高质量音频时间拉伸和音高移动库，提供 C 和 C++ API。由 Breakfast Quay（上游组织 breakfastquay）开发，是音频变速变调领域的标准引擎之一（soundtouch 的同行重件）。

**官方网站**: https://breakfastquay.com/rubberband/
**上游仓库**: https://github.com/breakfastquay/rubberband

## 功能特性

- **时间拉伸**: 改变音频速度而不影响音高
- **音高移动**: 改变音频音高而不影响速度
- **双引擎**: R2 (Faster) 快速引擎 + R3 (Finer) 高精度引擎
- **实时与离线**: 支持实时流式处理（RubberBandLiveShifter）和离线高质量处理（RubberBandStretcher）
- **跨平台**: C++11，meson 构建

## 版本历史

### 4.0.0 (当前版本)

- **构建系统**: meson + ninja
- **适配日期**: 2026-09-16
- **编译器**: clang 15.0.4 (OHOS aarch64)
- **状态**: built
- **依赖**: libsamplerate/0.2.2（重采样器）、boost/1.90.0.4.1（仅测试）
- **上游测试**: 8 个 meson test() 目标全过

## 使用方法

### C API

```c
#include <rubberband/rubberband-c.h>

RubberBandState rb = rubberband_new(sampleRate, channels,
                                    RubberBandOptionProcessRealTime,
                                    1.5, 1.0);  /* 拉伸 1.5 倍 */
rubberband_process(rb, input, numSamples, final);
int avail = rubberband_available(rb);
rubberband_retrieve(rb, output, avail);
rubberband_delete(rb);
```

### C++ API

```cpp
#include <rubberband/RubberBandStretcher.h>

using namespace RubberBand;
RubberBandStretcher stretcher(sampleRate, channels,
                              RubberBandStretcher::DefaultOptions,
                              1.0, 1.0);
stretcher.study(input, numSamples, true);
stretcher.process(input, numSamples, false);
stretcher.retrieve(output, available);
```

### 链接方式

```bash
pkg-config --cflags --libs rubberband
```

## 库文件

- **动态库**: librubberband.so.3.0.0
- **静态库**: librubberband.a
- **头文件**: rubberband/ 目录（RubberBandStretcher.h / RubberBandLiveShifter.h / rubberband-c.h）

## 相关链接

- **官方网站**: https://breakfastquay.com/rubberband/
- **GitHub**: https://github.com/breakfastquay/rubberband
- **API 文档**: https://breakfastquay.com/rubberband/code-doc/
- **历史归档**: archives/r/rubberband/3.3.0（旧版笔记，独立目录不覆盖）
