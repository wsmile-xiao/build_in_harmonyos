# ffmpeg-full 8.1.1 适配笔记

## 编译环境
- 构建系统: custom（ffmpeg自定义configure）
- 编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
source .build-context-ffmpeg-full-8.1.1
cd $BUILD_SRC_DIR

# 应用补丁
patch -p1 < patches/0001-configure-add-harmonyos-os-detection.patch

# 配置
export PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig:$DEFAULT_PREFIX/share/pkgconfig:$PKG_CONFIG_PATH
./configure \
  --prefix=$DEFAULT_PREFIX \
  --cc=clang --cxx=clang++ --host-cc=clang \
  --enable-cross-compile --arch=aarch64 --target-os=linux \
  --enable-shared \
  --enable-gpl --enable-version3 --enable-nonfree \
  --enable-libfreetype --enable-libharfbuzz --enable-libfribidi \
  --enable-libopus --enable-libvorbis \
  --enable-libopenjpeg --enable-libmp3lame --enable-libsoxr \
  --enable-openssl

# 编译和安装
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure无法识别HarmonyOS平台 | ffmpeg configure脚本中无harmonyos OS识别块 | 在configure的OS检测case语句中添加harmonyos分支，启用section_data_rel_ro和linux_perf |
| 2 | 运行时oc_mcenc_*符号未定义 | libtheora静态库缺少NEON汇编函数(oc_mcenc_search/refine4mv/refine1mv)，被--allow-shlib-undefined掩盖 | 移除--enable-libtheora和--extra-ldflags='-Wl,--allow-shlib-undefined' |

## 源码修改

补丁文件: `patches/0001-configure-add-harmonyos-os-detection.patch`

在configure脚本的OS检测case语句（第6242行附近）添加：
```
harmonyos)
    enable section_data_rel_ro
    enabled_any arm aarch64 && enable_weak linux_perf
    ;;
```

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| freetype | 2.14.3 | 字体渲染 |
| fribidi | 1.0.16 | 双向文本 |
| harfbuzz | 14.2.0 | 文本塑形 |
| opus | 1.5.2 | Opus音频编解码 |
| libvorbis | 1.3.7 | Vorbis音频编解码 |
| openjpeg | 2.5.3 | JPEG 2000编解码 |
| lame | 3.100 | MP3编码 |
| soxr | 0.1.3 | 音频重采样 |
| openssl | 3.5.0 | TLS支持 |

## 验证结果

```bash
$ ffmpeg --version
ffmpeg version 8.1.1 Copyright (c) 2000-2026 the FFmpeg developers
built with clang version 15.0.4
configuration: --prefix=/.../usr/local --cc=clang --cxx=clang++ --host-cc=clang
  --enable-cross-compile --arch=aarch64 --target-os=linux --enable-shared
  --enable-gpl --enable-version3 --enable-nonfree
  --enable-libfreetype --enable-libharfbuzz --enable-libfribidi
  --enable-libopus --enable-libvorbis --enable-libopenjpeg
  --enable-libmp3lame --enable-libsoxr --enable-openssl

$ ffmpeg -encoders | grep -E "opus|vorbis|mp3lame|openjpeg"
A....D libmp3lame    libmp3lame MP3 (MPEG audio layer 3) (codec mp3)
A....D libopus       libopus Opus (codec opus)
A....D libvorbis     libvorbis (codec vorbis)
VF.... libopenjpeg   OpenJPEG JPEG 2000 (codec jpeg2000)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ffmpeg-full-8.1.1-ohos-aarch64.tar.gz | 326MB | Release预编译包 |
| ffmpeg-full-8.1.1-ohos-aarch64-debug.tar.gz | 3.7MB | Debug符号包 |

## 注意事项

- ffmpeg使用自定义configure系统（非autotools），`--enable-cross-compile`是ffmpeg特有的选项
- libtheora编码器因NEON汇编函数缺失导致共享库链接失败，已禁用（内部VP3/Theora解码器仍可用）
- `--allow-shlib-undefined`会掩盖运行时链接错误，严禁使用
- 启用大量编解码库需要预先安装所有依赖预编译包

---
**编译结束**: 2026-05-27
**最终状态**: published