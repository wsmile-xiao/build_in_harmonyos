# ktimer

KTimer 是 KDE 定时提醒小工具（KDE release-service 26.04.0）：设定倒计时，
到点后执行指定命令 / 弹出通知，带系统托盘（StatusNotifierItem）与
`org.kde.ktimer` 的 D-Bus 单实例（KDBusService）。纯 Qt Widgets GUI，
无后台守护进程。

- 上游：https://invent.kde.org/utilities/ktimer
- 适配版本：26.04.0（`archives/k/ktimer/26.04.0/`）
- 构建系统：CMake + KDE ECM（`find_package(ECM REQUIRED NO_MODULE)`）
- 依赖基座：qtbase/6.11.1.1（FEATURE_dbus=ON，单一 Qt6 提供者）、
  kdbusaddons/6.29.0、statusnotifieritem/6.26.0、kio/6.14.0、
  kconfigwidgets/6.18.0、ki18n/kwidgetsaddons/knotifications/kcrash 6.18.0、
  kwindowsystem/6.18.0、karchive/6.19.0（对齐 kiconthemes 已发布二进制）、
  extra-cmake-modules/6.29.0（tool_requires）
- 依赖闭包：`conan graph info` 实测 rc=0、**仅 kio 一个包需本地重建**
  （其配方自带 `BUILD_TESTING=OFF` 不跑上游测试），其余全部命中已发布二进制
- 上游源码补丁：**无**（`patches_applied: []`）
- 上游测试：0（源码树无 tests/、CMakeLists 无 add_test；QA 由 KDE CI
  源码构建承担），由 `test_package/` 消费者冒烟测试补全
- 命令入口：`bin/ktimer`（见本目录 `commands.json`）
