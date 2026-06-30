# kvazaar

> Ultravideo HEVC (H.265) 编码器

## 简介

kvazaar 是一个开源的 HEVC (H.265) 视频编码器，由芬兰坦佩雷理工大学 (Tampere University of Technology)
的 Ultravideo 研究小组开发。它专注于高性能和低复杂度，适用于实时视频编码场景。

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 2.3.2 | published | 2026-06-18 |

## 构建信息

- **构建系统**: autotools (autoconf/automake/libtool)
- **语言**: C/C++
- **编译器**: clang 15.0.4
- **目标平台**: aarch64-unknown-linux-ohos (HarmonyOS)
- **配置**: `CONFIG_SHELL=bash bash ./configure --prefix=$DEFAULT_PREFIX`
- **依赖**: 无（可选: cryptopp, assembler）
- **许可**: 3-clause BSD + LGPLv2.1 (部分组件)

## 产物

- `bin/kvazaar` — HEVC 编码器 CLI 工具
- `lib/libkvazaar.so.7.5.0` — 共享库 (API 版本 7:5:0)
- `lib/libkvazaar.a` — 静态库
- `include/kvazaar.h` — 公共头文件
- `lib/pkgconfig/kvazaar.pc` — pkg-config 配置

## 使用示例

```bash
# 编码 YUV 视频为 HEVC
kvazaar -i input.yuv --input-res 1920x1080 -o output.265

# 使用预设
kvazaar -i input.yuv --input-res 1920x1080 -o output.265 --preset ultrafast
```

## 备注

- 在 HarmonyOS/aarch64 上使用 generic C 实现（无 SIMD 优化），功能完整
- GitHub archive 需运行 `autoreconf -fi` 生成 configure 脚本
- 需修复 HMDFS umask 077 问题（见 patches/0001-configure.patch）
