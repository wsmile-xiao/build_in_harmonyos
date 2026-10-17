# qtbase-opensource-src

`qtbase-opensource-src` packages the Qt 5 Base module for OpenHarmony PC.
Includes Core, Gui, Network, Test, Concurrent, OpenGLExtensions, DBus, Widgets,
PrintSupport and Xml libraries plus the qmake/moc/rcc development tools.

## Key adaptations for OHOS
- Abstract socket namespace patch (QLocalServer/QLocalSocket)
- pthread_cancel guard with HAVE_PTHREAD_CANCEL feature detection
- socklen_t fix for musl libc
- qmake OHOS host support (LD_LIBRARY_PATH fallback)
- No stripping (QMAKE_STRIP="")
- OpenGL ES 2 enabled for Qt3D consumers
- Qt5DBus enabled (dbus/1.14.10 dependency)
- 10 OHOS compatibility and test patches

## Modules
| Module | Library | Depends on |
|--------|---------|------------|
| Core | libQt5Core | zlib |
| Gui | libQt5Gui | Core, EGL, GLESv2 |
| Network | libQt5Network | Core |
| Test | libQt5Test | Core |
| Concurrent | libQt5Concurrent | Core |
| OpenGLExtensions | libQt5OpenGLExtensions (static) | Core, Gui |
| DBus | libQt5DBus | Core, dbus |
| Widgets | libQt5Widgets | Core, Gui |
| PrintSupport | libQt5PrintSupport | Core, Gui, Widgets |
| Xml | libQt5Xml | Core |
