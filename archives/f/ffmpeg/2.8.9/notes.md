# ffmpeg 2.8.9 适配笔记

## 编译环境
- 构建系统: autotools（ffmpeg 自定义 configure）
- 编译日期: 2026-05-27
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. 初始化构建: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build ffmpeg 2.8.9 --url=https://ffmpeg.org/releases/ffmpeg-2.8.9.tar.gz --no-download`
2. Configure:
   ```bash
   cd $BUILD_SRC_DIR
   ./configure --prefix=$DEFAULT_PREFIX --target-os=linux --arch=aarch64 --cc=clang --cxx=clang++ --ar=llvm-ar --nm=llvm-nm --ranlib=llvm-ranlib --disable-asm --disable-yasm --disable-inline-asm --disable-doc --disable-network --disable-debug --enable-shared --disable-ffserver
   ```
3. Make: `make -j2`
4. Install (staging): `make install DESTDIR=$TEST_PREFIX`
5. Install (local): `make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | C compiler test failed | ffmpeg 默认使用 gcc，但 OpenHarmony 只有 clang | 添加 `--cc=clang --cxx=clang++` |
| 2 | target_os 默认为 harmonyos | `uname -s` 返回 "HarmonyOS"，ffmpeg 不识别 | 使用 `--target-os=linux` |
| 3 | --disable-x86asm 不可用 | ffmpeg 2.8.9 老版本不支持此选项 | 使用 `--disable-asm --disable-yasm --disable-inline-asm` |

## 源码修改

无源码修改。ffmpeg 2.8.9 在 OpenHarmony 上编译无需修改任何源文件，仅需通过 configure 参数适配平台。

## 依赖版本

- clang 15.0.4
- make 4.4.1
- llvm-ar / llvm-nm / llvm-ranlib

## 验证结果

```bash
$ LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib /storage/Users/currentUser/usr/local/bin/ffmpeg -version
ffmpeg version 2.8.9 Copyright (c) 2000-2016 the FFmpeg developers
built with clang version 15.0.4
configuration: --prefix=/storage/Users/currentUser/usr/local --target-os=linux --arch=aarch64 --cc=clang --cxx=clang++ --ar=llvm-ar --nm=llvm-nm --ranlib=llvm-ranlib --disable-asm --disable-yasm --disable-inline-asm --disable-doc --disable-network --disable-debug --enable-shared --disable-ffserver
libavutil      54. 31.100 / 54. 31.100
libavcodec     56. 60.100 / 56. 60.100
libavformat    56. 40.101 / 56. 40.101
libavdevice    56.  4.100 / 56.  4.100
libavfilter     5. 40.101 /  5. 40.101
libswscale      3.  1.101 /  3. 1.101
libswresample   1.  2.101 /  1. 2.101
```

## 交付物

| 文件 | 说明 |
|------|------|
| ffmpeg-2.8.9-ohos-aarch64.tar.gz | 预编译包 |
| ffmpeg-2.8.9-ohos-aarch64-debug.tar.gz | debug 预编译包 |

## 注意事项

- ffmpeg 2.8.9 是老版本，configure 选项与最新版不同
- 必须使用 `--target-os=linux`，因为 HarmonyOS 内核是 Linux 变体
- 网络功能已禁用（--disable-network），如需启用需额外依赖
- ffserver 已禁用（此程序在新版本中已移除）
---

**编译结束**: 2026-05-27 16:18
**最终状态**: built
