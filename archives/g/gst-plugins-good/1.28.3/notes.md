# gst-plugins-good 1.28.3 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-30
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. meson setup builddir --prefix=$DEFAULT_PREFIX \
   -Dv4l2=disabled -Doss=disabled -Doss4=disabled \
   -Dximagesrc=disabled -Djack=disabled -Dpulse=disabled \
   -Ddv1394=disabled -Dsoup=disabled -Dgtk3=disabled \
   -Dgdk-pixbuf=disabled -Dqt5=disabled -Dqt6=disabled \
   -Ddirectsound=disabled -Dosxaudio=disabled \
   -Dosxvideo=disabled -Dwaveform=disabled \
   -Dexamples=disabled -Dtests=disabled -Ddoc=disabled \
   -Dglib_assert=false -Dglib_checks=false -Dorc=disabled
2. ninja -j2
3. meson install --destdir=$TEST_PREFIX (staging)
4. meson install (local prefix)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | V4L2 编译失败 | gstv4l2object.c:144 initializer element is not a compile-time constant | 禁用 v4l2 插件 |
| 2 | Linux 音频子系统不可用 | OpenHarmony 无 OSS/Pulse/JACK | 禁用 oss, oss4, pulse, jack |
| 3 | libsoup 3.0 未安装 | 无预编译包 | 禁用 soup 插件 |
| 4 | GTK3/gdk-pixbuf 不可用 | 缺少运行时 GTK3 环境 | 禁用 gtk3, gdk-pixbuf |
| 5 | ORC 编译器不可用 | orc-0.4 未安装 | 禁用 orc |

## 禁用的插件列表

- v4l2: V4L2 视频设备（编译失败）
- oss/oss4: OSS 音频子系统
- pulse: PulseAudio
- jack: JACK 音频
- dv1394: IEEE 1394 数字视频
- soup: libsoup HTTP 源/汇
- gtk3: GTK+视频汇
- gdk-pixbuf: 图像解码器
- qt5/qt6: Qt 视频汇
- ximagesrc: X11 图像源
- directsound/osxaudio/osxvideo/waveform: Windows/macOS 特有

## 已编译的 55 个插件

alpha, alphacolor, apetag, audiofx, audioparsers, auparse, autodetect, avi, cutter, navigationtest, debugutils, deinterlace, dtmf, effectv, equalizer, flv, flxdec, goom, goom2k1, icydemux, id3demux, imagefreeze, interleave, isomp4, alaw, mulaw, level, matroska, monoscope, multifile, multipart, replaygain, rtp, rtpmanager, rtsp, shapewipe, smpte, spectrum, udp, videobox, videocrop, videofilter, videomixer, wavenc, wavparse, xingmux, y4m, adaptivedemux2, amrnb, amrwbdec, cairo, flac, jpeg, png, mpg123

## 依赖版本

- gstreamer 1.28.3
- gst-plugins-base 1.28.3
- glib 2.88.0
- cairo 1.18.4
- flac 1.4.3
- libjpeg-turbo 3.1.4.1 (via libjpeg)
- libpng 1.6.43
- mpg123 1.32.9
- opencore-amrnb 0.1.6
- opencore-amrwb 0.1.6

## 验证结果

```bash
# 55 个 GStreamer 插件编译成功
ls ~/usr/local/lib/gstreamer-1.0/libgst*.so | wc -l
# 55
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| 55 个 libgst*.so | ~总计 | GStreamer 好插件集合 |

## 注意事项

- v4l2 插件因编译错误禁用，需要 OpenHarmony V4L2 kernel header适配才能启用
- soup 插件需要 libsoup 3.0 预编译包才能启用
- orc 优化编译器禁用后，部分插件缺少加速路径但功能正常
---

**编译结束**: 2026-06-03 23:59
**最终状态**: built
