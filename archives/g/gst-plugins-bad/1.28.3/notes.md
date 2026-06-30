# gst-plugins-bad 1.28.3 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-30
- 编译器: clang 15.0.4 / clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 链接器: ld.lld 15.0.4
- 状态: built

## 编译步骤

```bash
source .build-context-gst-plugins-bad-1.28.3
cd $BUILD_SRC_DIR

# meson 配置（builddir 在源码外，避免 HMDFS 限制）
meson setup builddir \
  --prefix=$DEFAULT_PREFIX \
  -Ddoc=disabled \
  -Dexamples=disabled \
  -Dtests=disabled \
  -Dgl=disabled \
  -Dopensles=disabled \
  -Dorc=disabled \
  -Dwebp=disabled

# 编译
ninja -C builddir -j1

# staging 安装
ninja -C builddir install DESTDIR=$TEST_PREFIX

# 本地安装
ninja -C builddir install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GL 插件编译失败 | OHOS GL 头文件冲突：GL_CONTEXT_PROFILE_MASK 等宏未定义 | `-Dgl=disabled` 禁用 GL 插件 |
| 2 | OpenSLES 插件编译失败 | Android OpenSLES_Android.h 不存在于 OHOS | `-Dopensles=disabled` 禁用 opensles 插件 |
| 3 | webp 插件链接失败 | libwebp 静态库符号冲突（SharpYuvInit/SharpYuvConvert） | `-Dwebp=disabled` 禁用 webp 插件 |
| 4 | meson builddir 不能在源码内 | HMDFS 文件系统限制 | builddir 放在源码目录外 `$BUILD_SRC_DIR/builddir` |
| 5 | 部分 sys 子目录缺失 | 源码 tarball 中 nvcodec 等子目录缺失，需从 .orig 复制 | 从 `.orig` 复制 15 个 sys 子目录到 `.work` |

## 源码修改

无补丁文件。源码修改仅涉及：
- 从 .orig 复制缺失的 sys 子目录（nvcodec 等 15 个目录）以通过 meson 配置

## 依赖版本

| 依赖 | 版本 |
|------|------|
| gstreamer | 1.28.3 |
| gst-plugins-base | 1.28.3 |
| glib | 2.88.0 |
| openssl | 1.1.1w |
| libdrm | 2.4.133 |
| libxml2 | 2.15.3 |
| cairo | 1.18.4 |
| libwebp | 1.3.2 (未使用，已禁用) |
| libsndfile | (可用) |
| libbz2 | (可用) |
| libopus | (可用) |
| libsbc | (可用) |
| dtls/openssl | 1.1.1w |

## 验证结果

```bash
# 91 个 GStreamer 插件 .so 文件已安装
ls ~/usr/local/lib/gstreamer-1.0/*.so | wc -l
# 91

# 18 个库 .so 文件已安装
ls ~/usr/local/lib/libgst*-1.0.so | wc -l
# 18

# 14 个 pkg-config 文件已安装
ls ~/usr/local/lib/pkgconfig/gstreamer-*.pc | wc -l
# 14

# 质量门禁：PASS
```

### 已构建的 91 个插件列表

accurip, adpcmdec, adpcmenc, aes, aiff, analyticsoverlay, asfmux, audiobuffersplit, audiofxbad, audiolatency, audiomixmatrix, audiovisualizers, autoconvert, bayer, bluez, bz2, camerabin, closedcaption, codec2json, codecalpha, codectimestamper, coloreffects, colormanagement, dash, debugutilsbad, dtls, dvb, dvbsubenc, dvbsuboverlay, dvdspu, faceoverlay, fbdevsink, festival, fieldanalysis, freeverb, frei0r, gaudieffects, gdp, geometrictransform, hls, id3tag, insertbin, inter, interlace, ipcpipeline, ivfparse, ivtc, jp2kdecimator, jpegformat, ladspa, legacyrawparse, midi, mpegpsdemux, mpegpsmux, mpegtsdemux, mpegtsmux, mse, mxf, netsim, opusparse, pcapparse, pnm, proxy, removesilence, rfbsrc, rist, rtmp2, rtpmanagerbad, rtponvif, sbc, sdpelem, segmentclip, shm, siren, smooth, smoothstreaming, sndfile, speed, subenc, switchbin, tensordecoders, timecode, transcode, ttmlsubs, unixfd, videofiltersbad, videoframe_audiolevel, videoparsersbad, videosignal, vmnc, vulkan

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| gst-plugins-bad-1.28.3-ohos-aarch64.tar.gz | 42MB | 预编译包（含 91 个插件 + 18 个库 + pkg-config） |
| gst-plugins-bad-1.28.3-ohos-aarch64-debug.tar.gz | 63MB | 预编译调试包 |

## 注意事项

1. GL 插件必须禁用（OHOS 平台无完整 OpenGL 支持）
2. opensles 插件必须禁用（非 Android 平台）
3. webp 插件必须禁用（libwebp 静态库符号冲突）
4. orc 可选禁用（本构建已禁用，无 Orc 优化但减少依赖）
5. vulkan 插件已构建但需 libdrm 支持
6. gst-inspect-1.0 在 OHOS 上运行需 LD_LIBRARY_PATH 设置正确
---

**编译结束**: 2026-06-03 23:59
**最终状态**: built
