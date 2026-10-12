# Qt 6

Qt is a cross-platform C++ framework for building application user interfaces and services. This archive packages the QtBase 6.0.0 subset adapted for HarmonyOS PC.

## Features

- Qt Core, Concurrent, Network, raster Qt Gui, offscreen Qt Widgets, PrintSupport, Test, and Xml.
- CMake and qmake integration, including Qt host tools.
- Qt Network TLS using the HarmonyOS OpenSSL 3 runtime.
- UID-scoped HarmonyOS abstract local sockets with peer-credential checks for managed Qt listeners.

## HarmonyOS PC adaptation

This version targets HarmonyOS 6.0 on AArch64 with the HarmonyOS Clang toolchain. Its CMake platform and qmake mkspec keep Qt's POSIX/Linux behavior while selecting the HarmonyOS SDK.

Relative `QLocalServer` names use Qt-managed abstract AF_UNIX addresses. The server checks `SO_PEERCRED` before accepting a managed connection. Device testing covered two app-clone instances with distinct UIDs: the client reached the endpoint, while the server rejected the foreign UID before Qt accepted a connection. A separate HAP-to-SSH system-UID probe was denied by HarmonyOS with `EACCES` at the native socket boundary, before Qt was involved; cross-security-domain access is not part of the supported guarantee.

HarmonyOS may reject absolute pathname AF_UNIX binds with `EROFS`; the corresponding Qt test records this platform limitation and skips that pathname-only case. The SDK also lacks resolver functions used by some `QDnsLookup` cases, which are recorded as expected failures. TLS was verified with the device's OpenSSL 3.6.4 runtime.

This archive is a QtBase feature subset. It does not include Qt Quick or a window-system integration plugin; Widgets is configured for offscreen use.

## Dependencies

- Build: HarmonyOS 6.0 SDK, AArch64 Clang/Clang++, CMake, and Conan 2.
- Runtime: HarmonyOS system libraries; OpenSSL 3 is used when TLS is enabled.
- The Conan recipe declares no Conan package dependencies.

## References

- [QtBase documentation](https://doc.qt.io/qt-6/qtbase-index.html)
- [QtBase 6.0.0 source](https://github.com/qt/qtbase/tree/v6.0.0)
