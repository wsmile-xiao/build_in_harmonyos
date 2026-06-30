# qt5-qtgraphicaleffects 5.15.2 Build Notes

## Source
- Local source at ~/tmp/qt5-qtgraphicaleffects-src/

## Build System
- qmake (Qt5 addon module, QML plugin)
- Requires qtdeclarative (Qt Quick/QML module) - NOT just qtbase

## Dependency Resolution
- Initially qtdeclarative was not installed in ~/usr/local/Qt5/
- The .pro file has: `requires(qtHaveModule(quick))` - hard dependency on Qt Quick
- Had to build and install qt5-qtdeclarative first
- qtdeclarative also needed qlalr tool to be ELF-signed on HarmonyOS
- libc++_shared.so from OHOS SDK needed for Qt5 tools to work

## Build Steps
1. Build qt5-qtdeclarative first and install to ~/usr/local/Qt5/
2. cd ~/tmp/qt5-qtgraphicaleffects-src
3. qmake qtgraphicaleffects.pro
4. make -j2
5. make install

## Issues Encountered
- qlalr: "Operation not permitted" → ELF signing fix
- libc++_shared.so missing → copy from OHOS SDK + sign
- qmlcachegen: "Operation not permitted" → ELF signing fix
- HMDFS symlink issues → rm -f && ln -s workaround

---

**编译结束**: 2026-05-31 03:17
**最终状态**: built