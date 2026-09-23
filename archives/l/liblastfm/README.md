# liblastfm

Last.fm 官方 C++/Qt5 客户端库：Scrobble 提交（Audioscrobbler）、
Web Service API（artist/album/track/tag/chart）、Radio 调台。

上游：https://github.com/lastfm/liblastfm（1.2.0 系，git snapshot
81e8f9dc16@2025-02-22）。上游默认分支目标 Qt6；本仓适配基于 Qt5
（BUILD_WITH_QT5=ON，上游 CMakeLists 原生开关）。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.2.0-git20250222.81e8f9d | built | 首次适配（HarmonyOS PC aarch64，Qt5 线） |

## 依赖

- qt5-qtbase/5.15.2.2（Core/Network/Xml/Test/DBus）

## 产物

- liblastfm5.so（主库；fingerprint 子库因强制依赖 samplerate+fftw3f
  按"可关则关"原则关闭 BUILD_FINGERPRINT=OFF，非 Scrobble/WebService
  核心能力）
