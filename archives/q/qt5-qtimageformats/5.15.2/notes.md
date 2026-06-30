# Build Notes — qt5-qtimageformats 5.15.2

## Build Info
- Software: qt5-qtimageformats
- Version: 5.15.2
- Build System: qmake
- Qt5 Prefix: /storage/Users/currentUser/usr/local/Qt5

## Build Steps
1. Set Qt5 environment (PATH, QTDIR)
2. qmake qtimageformats.pro (in source directory)
3. make -j2
4. make install (installs to Qt5 prefix)

## Installed Files
- plugins/imageformats/libqtga.so
- plugins/imageformats/libqwbmp.so
- plugins/imageformats/libqtiff.so
- plugins/imageformats/libqwebp.so
- plugins/imageformats/libqicns.so
- lib/cmake/Qt5Gui/Qt5Gui_QTgaPlugin.cmake
- lib/cmake/Qt5Gui/Qt5Gui_QWbmpPlugin.cmake
- lib/cmake/Qt5Gui/Qt5Gui_QTiffPlugin.cmake
- lib/cmake/Qt5Gui/Qt5Gui_QWebpPlugin.cmake
- lib/cmake/Qt5Gui/Qt5Gui_QICNSPlugin.cmake

## Configure Summary
- TIFF: yes (built-in)
- WEBP: yes (built-in)
- JasPer: no
- MNG: no

## Notes
- Qt5 addon module using qmake build system
- No patches needed for HarmonyOS/OHOS build
- Source obtained via git clone
---

**编译结束**: 2026-05-31 01:42
**最终状态**: built
