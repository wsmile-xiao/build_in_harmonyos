# Test Report

Status: PASS
RC: 0
Date: 2026-09-17 (round 2: x11/xshm/xvideo/xi/drm/iso-codes enabled)
Duration: ~360s
Log: local conan create output (2026-09-17, not committed per rule 19; package cache and build log retained on worker)

## Test Details

### conan create
- Build: PASS (40 .a files, 41 .pc files, 138 .h files packaged)
- Configuration: meson, static, OHOS aarch64
- Command: `conan create archives/g/gst-plugins-base/1.28.3 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --build="gst-plugins-base/*"`

### test_package
- Build: PASS (test_gst_plugins_base compiled and linked)
- Test: PASS

```
gstreamer version: GStreamer 1.28.3
audio format S16 depth: 16
video format I420 bits: 8
gst-plugins-base test: PASS
```

### APIs verified (5 calls, 3 explicit g_assert)
- gst_init() - GStreamer initialization
- gst_version_string() - version query (g_assert)
- gst_pb_utils_init() - pbutils library (gst-plugins-base)
- gst_audio_format_get_info() - audio library (gst-plugins-base) (g_assert)
- gst_video_format_get_info() - video library (gst-plugins-base) (g_assert)

## Plugins built (29)
- Base plugins: adder, app, audioconvert, audiomixer, audiorate, audioresample,
  audiotestsrc, compositor, debugutils (basedebug), dsd, encoding, gio,
  overlaycomposition, pbtypes, playback, rawparse, subparse, tcp, typefind
  (typefindfunctions), videoconvertscale, videorate, videotestsrc, volume
- External dependency plugins: ogg, vorbis, opus, alsa
- X11 video sinks (round 2): ximagesink, xvimagesink

## Libraries built (11)
gstallocators (with DRM dumb buffer allocator), gstapp, gstaudio, gstfft,
gstpbutils (with iso-codes language name lookup in gst-tag), gstriff, gstrtp,
gstrtsp, gstsdp, gsttag, gstvideo

## Disabled features (dependency ecosystem gaps, see notes.md)
- pango: registry pango requires glib/2.84.0.1 vs glib2/2.88.0 conflict
- gl: no GL API library (gl/glesv2/opengl) published in registry
- theora/tremor/cdparanoia/libvisual: deps not published in registry
