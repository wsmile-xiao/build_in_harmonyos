# qt5-qtsvg 5.15.2 Build Notes

## Source
- Official Qt mirror: qtsvg-everywhere-src-5.15.2.tar.xz
- sha256: 8bc3c2c1bc2671e9c67d4205589a8309b57903721ad14c60ea21a5d06acb585e

## Build System
- qmake (Qt5 addon module, not CMake)
- Uses qt5-qtbase/5.15.2 from Conan artifact repo

## Key Adaptation Points
1. **qt5-qtbase path fix**: The qt5-qtbase Conan package has qt.conf and .pri files
   that point to the build directory instead of the package directory. The
   conanfile.py build() method fixes these paths before running qmake.
2. **Stripping prevention**: QMAKE_STRIP="" is used because OHOS loader rejects
   stripped ELF files.
3. **No source modifications needed**: qtsvg builds cleanly on HarmonyOS with
   the linux-clang mkspec.

## Build Steps
1. conan install qt5-qtbase (from artifact repo)
2. Fix qt.conf and .pri files in qt5-qtbase package
3. qmake qtsvg.pro -spec linux-clang
4. make -j2 QMAKE_STRIP=""
5. Package: libQt5Svg.so, plugins, headers, cmake configs, mkspecs

## Build Artifacts
- lib/libQt5Svg.so.5.15.2 — main SVG rendering library
- plugins/imageformats/libqsvg.so — SVG image format plugin
- plugins/iconengines/libqsvgicon.so — SVG icon engine plugin
- include/QtSvg/ — public headers
- lib/cmake/Qt5Svg/ — CMake config files
- mkspecs/modules/qt_lib_svg.pri — qmake module config

**编译结束**: 2026-08-08
**最终状态**: built
