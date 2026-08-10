# Build Notes — qt5-qtimageformats 5.15.2

## Build Info
- Software: qt5-qtimageformats
- Version: 5.15.2
- Build System: qmake
- Qt5 Dependency: qt5-qtbase/5.15.2.1

## Build Steps
1. Source: qtimageformats-everywhere-src-5.15.2.tar.xz from Qt mirror
2. qmake qtimageformats.pro (using qmake from qt5-qtbase)
3. make -j4 QMAKE_STRIP="" (prevent stripping, OHOS rejects stripped ELF)
4. Package: copy plugins and cmake configs

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
- TIFF: yes (bundled libtiff)
- WEBP: yes (bundled libwebp)
- TGA: yes (built-in)
- WBMP: yes (built-in)
- ICNS: yes (requires regularexpression, provided by Qt5Core)
- JasPer: no
- MNG: no

## Notes
- Qt5 addon module using qmake build system
- Depends on qt5-qtbase/5.15.2.1 for qmake tool, Qt5Core, Qt5Gui
- No patches needed for HarmonyOS/OHOS build
- Bundled 3rdparty libtiff and libwebp are used (no external system dependencies)
- QMAKE_STRIP="" to prevent stripping (OHOS loader rejects stripped ELF files)
---

**编译结束**: 2026-08-08 03:57
**最终状态**: built
