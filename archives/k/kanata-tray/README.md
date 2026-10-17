# kanata-tray

Tray Icon for Kanata —— 系统托盘图标，用于控制 kanata 键盘重映射器（Go GUI 应用）。支持启动/停止/暂停、多配置预设切换、图层图标、hooks 与 TCP 控制服务器。

- 上游: https://github.com/rszyma/kanata-tray
- 版本: 0.8.0
- 许可证: GPL-3.0-or-later
- 构建: Go modules + cgo（getlantern/systray，需 GTK3 + libayatana-appindicator3 开发头），`go build .`
