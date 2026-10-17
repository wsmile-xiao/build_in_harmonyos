# ayatana-indicator-session

Ayatana Indicators 会话指示器 D-Bus 服务，注册 `org.ayatana.indicator.session` bus 名，
提供桌面会话菜单（关机/重启/注销/锁屏/挂起/用户切换等），面向 Unity/Lomiri 等桌面。

- 上游仓库: https://github.com/AyatanaIndicators/ayatana-indicator-session
- 构建系统: CMake (cmake_minimum 3.13)
- 依赖: libayatana-common >= 0.9.2, glib-2.0 >= 2.36, gio-unix-2.0 >= 2.36
- 许可证: GPL-3.0

## 版本

- 26.6.1 — 最新稳定版

## 产物

服务可执行文件 `ayatana-indicator-session-service`（安装于 `bin/`），OHOS 适配说明见
`26.6.1/notes.md`。
