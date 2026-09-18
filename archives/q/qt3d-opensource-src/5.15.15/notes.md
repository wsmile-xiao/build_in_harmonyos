# qt3d-opensource-src 5.15.15 Conan Adaptation Notes

## Software Information

- **Software**: qt3d-opensource-src (Qt3D module for Qt5)
- **Version**: 5.15.15
- **Build system**: qmake
- **Target platform**: HarmonyOS (aarch64-linux-ohos)
- **Source**: https://download.qt.io/archive/qt/5.15/5.15.15/submodules/qt3d-everywhere-opensource-src-5.15.15.tar.xz

## Dependencies

- qt5-qtbase/5.15.2.2 (provides Qt5Core, Qt5Gui, Qt5Network, qmake, mkspecs)
- qt5-qtdeclarative/5.15.2 (provides Qt5Qml, Qt5Quick for Qt3D Quick modules)

## Historical Reference

This recipe is the Conan adaptation of the previously built qt5-qt3d 5.15.2
(archives/q/qt5-qt3d/5.15.2/). The historical adaptation noted:
- No source modifications required
- Qt3D bundles assimp internally for 3D model loading
- Built successfully with qmake against qt5-qtbase 5.15.2

## Build Process

1. Fix qt5-qtbase package relocatability (qt.conf, .pri files)
2. Merge qt5-qtdeclarative mkspecs/modules .pri files into qtbase's mkspecs
   (qmake only scans qtbase's mkspecs; without the merge all Qt53DQuick*
   modules are silently skipped by qtHaveModule(qml)/qtHaveModule(quick))
3. Set up Qt5 environment: PATH, QTDIR, LD_LIBRARY_PATH
4. qmake -spec linux-clang qt3d.pro
5. make -jN QMAKE_STRIP="" (prevent stripping; OHOS rejects stripped ELF)
6. Package: libraries, headers, plugins, QML plugins, mkspecs, bin

## Products

### Libraries (12 shared libraries)
- libQt53DCore, libQt53DRender, libQt53DInput, libQt53DLogic
- libQt53DAnimation, libQt53DExtras
- libQt53DQuick, libQt53DQuickRender, libQt53DQuickInput
- libQt53DQuickAnimation, libQt53DQuickExtras, libQt53DQuickScene2D

### Executable
- qgltf

### QML Plugins
- Qt3D/Core, Input, Render, Animation, Extras, Scene2D

## Platform Adaptation

No source modifications needed. Qt3D source code does not contain UNIX/LINUX
conditional macros requiring changes. Qt's mkspecs uses linux-clang configuration
which is compatible with OHOS.

## Version Compatibility

Qt3D 5.15.15 is built against qt5-qtbase 5.15.2.2 and qt5-qtdeclarative 5.15.2.
Qt 5.15 is an LTS series; all 5.15.x patch versions share the same ABI.
The conan recipe specifies these dependency versions as they are the latest
published versions in the project registry.

## Notes

- SHA256 obtained from Qt official release checksums
  (download.qt.io ...tar.xz.sha256): 5a400db06eb676dab23f9d4d25805bf051e38380b9b37ade3340cc2c3130db73
- make jobserver mkfifo "Operation not permitted" warning is non-blocking
- assimp deprecated warnings (C++ copy constructor/assignment) are non-blocking

---

**Adaptation date**: 2026-08-27
**Status**: built (recipe created, pending CI verification)
