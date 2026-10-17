# libayatana-indicator

Ayatana Indicators 核心库：为桌面面板（panel）提供指示器插件的加载与管理框架，
是 MATE/Xfce 等桌面环境指示器体系（音量/网络/电源等）的基础库。

## 功能概述

- `IndicatorObject`：指示器插件基类（GObject 派生），定义 entry/image/menu 接口
- `IndicatorService` / `IndicatorServiceManager`：指示器服务的 D-Bus 生命周期管理
- `IndicatorDesktopShortcuts`：解析 .desktop 文件的快捷方式段
- `indicator-ng`：新一代指示器加载（配合 libayatana-ido）
- `ayatana-indicator-loader3`：运行时加载 libayatana-indicators3/ 下插件的工具

## OHOS 适配

- 构建系统 CMake（>=3.13），依赖经 pkg_check_modules 解析，适配重点见
  [0.9.5/notes.md](0.9.5/notes.md)
- 上游测试全部依赖 dbus-test-runner/Xvfb 桌面环境，离线 CI 不可执行，
  离线验证由 test_package 承担
- 库本身无 X11 硬依赖（GTK 经 broadwayd 无头后端可实例化），但
  `IndicatorService` 系 API 运行时需要 D-Bus session bus

## 依赖关系

- 编译/运行：glib（gio-unix）、gtk3、ayatana-ido（ENABLE_IDO）
- 运行时（部分 API）：D-Bus session bus

## 参考资料

- 上游仓库：https://github.com/AyatanaIndicators/libayatana-indicator
- Ayatana Indicators 组织：https://ayatanaindicators.github.io/
