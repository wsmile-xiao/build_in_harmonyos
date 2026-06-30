# qt5-qtsvg 5.15.2 Build Notes

## Source
- Local source at ~/tmp/qt5-qtsvg-src/

## Build System
- qmake (Qt5 addon module, not CMake)
- qt-configure-module not available in this Qt5 installation, using qmake directly

## Build Steps
1. qmake qtsvg.pro
2. make -j2
3. make install DESTDIR=...
4. make install
---

**编译结束**: 2026-05-31 01:48
**最终状态**: built
