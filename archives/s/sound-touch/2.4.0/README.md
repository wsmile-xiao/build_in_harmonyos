# SoundTouch 2.4.0 — OHOS aarch64 预编译包

## 软件介绍

SoundTouch 是一个开源音频处理库，可独立调整音频的节奏(tempo)、音高(pitch)
和播放速率(rate)，而不相互影响。常用于音乐播放器、DJ 工具和音频分析软件。

- **官网**: http://www.surina.net/soundtouch/
- **许可证**: LGPL v2.1
- **版本**: 2.4.0

## 包内容

```
bin/soundstretch           — 命令行音频处理工具
lib/libSoundTouch.so.1     — 主共享库 (含符号链接)
lib/libSoundTouchDll.so.1  — DLL 包装器 (含符号链接)
include/soundtouch/        — 开发头文件 (6个)
lib/pkgconfig/soundtouch.pc — pkg-config 文件
```

## 使用方法

### 命令行工具 soundstretch

```bash
# 改变节奏 (加快50%)
soundstretch input.wav output.wav -tempo=50

# 改变音高 (提升3个半音)
soundstretch input.wav output.wav -pitch=3

# 改变播放速率 (加快30%)
soundstretch input.wav output.wav -rate=30

# 组合使用
soundstretch input.wav output.wav -tempo=30 -pitch=-2
```

### C++ 开发链接

```bash
# 编译链接示例
clang++ -o myapp myapp.cpp \
  $(pkg-config --cflags --libs soundtouch)
```

### pkg-config 信息

```
版本:    2.4.0
头文件:  -I${prefix}/include/soundtouch
库文件:  -L${prefix}/lib -lSoundTouch
```

## 已知平台限制

- NEON 汇编优化已禁用 (`--disable-neon-optimizations`)
- 库依赖仅 libc++_shared.so 和 libc.so (最小依赖集)
- `__powidf2` 软浮点符号已静态吸收到库内部，无需额外运行时依赖

## 测试状态

功能测试全部通过 (19/19):
- 版本验证: 4项 ✅
- WAV 音频处理: 3项 ✅ (tempo/pitch/rate 三种变换)
- 符号依赖: 6项 ✅
- 头文件: 6项 ✅

详细测试报告见 `reports/test-report.md`。