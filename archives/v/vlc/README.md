# vlc

VLC media player 核心库（VideoLAN）：libvlc（稳定 C API）+ libvlccore +
~280 个运行时动态加载插件（demux/codec/audio_filter/video_filter/access/
stream_out/text_renderer/visualization...）。

## 版本索引

| 版本 | 状态 | 说明 |
|------|------|------|
| 3.0.23 | built | OHOS aarch64 适配（2026-09-25），见 [3.0.23/](3.0.23/) |

## 依赖

- ffmpeg/4.4.8（avcodec/avformat/swscale）
- codec 链：libmad / libogg / libvorbis / libtheora / flac / libopus /
  dav1d / libvpx / x264 / x265
- 播放链：libdvdnav / fribidi / libass（freetype/fontconfig/harfbuzz 传递）

## 平台适配说明

- OHOS 裁剪：无 X/Wayland 桌面栈（xcb/wayland/qt/skins2/notify/ncurses 全禁）
- OHOS musl 能力边界：posix_close / pthread_cancel 系 API 守卫（见 3.0.23/patches/）
- classic OpenGL 禁用（OHOS 无 libGL.so；GLES2 保持上游默认 disabled）
- 消费者入口：`#include <vlc/vlc.h>`，链接 -lvlc（libvlccore 由 SONAME 传递）；
  运行时需 VLC_PLUGIN_PATH 指向 lib/vlc/plugins（libvlc_new 初始化插件系统）
