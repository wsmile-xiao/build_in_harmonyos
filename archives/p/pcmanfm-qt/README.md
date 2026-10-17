# pcmanfm-qt

pcmanfm-qt 是 LXQt 桌面环境的 Qt6 文件管理器，基于 libfm-qt 构建。

## 版本信息

| 版本 | 状态 | 日期 |
|------|------|------|
| 2.4.0 | built | 2026-09-01 |

## OHOS 适配要点

- Qt6DBus：OHOS 无 D-Bus 会话总线，`application.cpp` 的单实例 DBus 服务与
  `org.freedesktop.FileManager1` 相关代码路径已移除，`qt6_add_dbus_adaptor()`
  调用删除。
- Qt6LinguistTools：OHOS 无 lrelease/lupdate 工具，配方以 stub 满足
  `find_package(Qt6LinguistTools)`，`lxqt_translate_ts()` 成为 no-op。
- LayerShellQt：Wayland 专属，OHOS 无此组件，桌面背景层代码与链接已移除。
- X11：`desktopwindow.cpp` 中 EWMH / `QX11Application` 相关代码移除
  （OHOS 无 X11，qtbase 不提供 QX11Application）。
- autostart：上游安装到 `/etc/xdg/autostart` 绝对路径，改为安装到
  包内数据目录（免 root 权限）。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| qtbase | 6.11.1 | Qt6 GUI/Widgets 基础模块 |
| libfm-qt | 2.4.0 | Qt6 文件管理核心库 |
| lxqt2-build-tools | 2.4.0 | LXQt CMake 辅助模块 |

## 功能验证

```bash
# test_package：验证打包可执行文件存在，且 QT_QPA_PLATFORM=offscreen 下
# pcmanfm-qt --help 正常启动退出（无显示服务器环境）
```

## 参考

- 源码: https://github.com/lxde/pcmanfm-qt