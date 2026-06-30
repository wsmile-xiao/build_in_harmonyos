# fluid-synth 2.4.6 编译笔记

## 编译信息
- 软件版本: 2.4.6
- 编译日期: 2026-06-01
- 构建系统: CMake (非 autotools)
- 编译器: clang 15.0.4
- 安装前缀: ~/usr/local

## 编译配置
- BUILD_SHARED_LIBS=OFF (静态库)
- 禁用所有音频后端 (ALSA, JACK, PulseAudio, PipeWire, SDL2/3, OSS, aufile)
- 禁用 libsndfile (无 SF3 支持)
- 禁用 D-Bus, systemd, LADSPA, libinstpatch, readline, network, IPv6, OpenMP
- CMAKE_C_STANDARD=99

## 关键适配问题及解决方案

### 1. lld linker 依赖 libxml2.so.16 问题
**问题**: OpenHarmony 的 musl 动态链接器不搜索 LD_LIBRARY_PATH 或 RUNPATH，
仅搜索 /etc/ld-musl-aarch64.path 中列出的系统路径。OHOS SDK 的 lld 需要 
libxml2.so.16 但无法找到它。

**解决方案**: 使用 GNU ld 替代 lld，通过 CMake 标志:
- `CMAKE_C_FLAGS="-fuse-ld=/data/service/hnp/bin/ld"`
- `CMAKE_EXE_LINKER_FLAGS="-fuse-ld=/data/service/hnp/bin/ld"`
- `CMAKE_SHARED_LINKER_FLAGS="-fuse-ld=/data/service/hnp/bin/ld"`

### 2. gentables ExternalProject 编译失败
**问题**: gentables 子项目的 CMake CONFIGURE_COMMAND 不继承父项目的链接器标志，
导致 gentables 内部的 CMake try-compile 也使用 lld 并失败。

**解决方案**: 修改 src/CMakeLists.txt 的 ExternalProject_Add 配置，在 CONFIGURE_COMMAND
中添加 `-DCMAKE_C_FLAGS="-fuse-ld=..."` 和 `-DCMAKE_EXE_LINKER_FLAGS="-fuse-ld=..."`。

### 3. make_tables.exe ELF 签名
**问题**: 编译生成的 make_tables.exe 未签名，无法在 OpenHarmony 上执行。

**解决方案**: 使用 `binary-sign-tool sign -selfSign 1` 进行自签名。

### 4. fluidsynth 二进制签名
**问题**: 安装后的 fluidsynth 二进制需要 ELF 签名才能执行。

**解决方案**: 使用 `binary-sign-tool sign -selfSign 1` 签名。

## 依赖
- glib-2.0 (2.88.0) - 本地预编译包 (静态库)
- libsndfile - 禁用（无本地可用版本）

## 本地验证结果
```
$ fluidsynth --version
FluidSynth runtime version 2.4.6
Copyright (C) 2000-2025 Peter Hanappe and others.
Distributed under the LGPL license.
SoundFont(R) is a registered trademark of Creative Technology Ltd.

FluidSynth executable version 2.4.6
Sample type=double
```

## 打包产物
- fluid-synth-2.4.6-ohos-aarch64.tar.gz (2101KB)
- fluid-synth-2.4.6-ohos-aarch64-debug.tar.gz (1454KB)

## 补丁
- 0001-gentables-gnu-ld-linker.patch: 为 gentables ExternalProject 传递 GNU ld 链接器标志
---

**编译结束**: 2026-06-02 16:31
**最终状态**: built
