# gst-plugins-ugly 1.28.3 for OpenHarmony

A set of GStreamer plugins that have licensing issues or are potentially
patent-encumbered. This build includes the following plugins:

- **asf**: ASF (Windows Media) file format plugin
- **dvdlpcmdec**: DVD LPCM audio decoder
- **dvdsub**: DVD subtitle decoder
- **realmedia**: RealMedia file format plugin

Note: GPL-licensed plugins (x264, cdio, dvdread, mpeg2dec) are NOT enabled
in this build.

## Build Information

- **Version**: 1.28.3
- **Build System**: meson
- **Compiler**: clang 15.0.4 (OHOS toolchain)
- **Architecture**: aarch64
- **Status**: published

## Dependencies

- gstreamer-1.0 >= 1.28.3
- gst-plugins-base-1.0 >= 1.28.3
- glib-2.0 >= 2.88.0
