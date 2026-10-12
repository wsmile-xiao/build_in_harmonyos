# NetworkManagerQt (KDE Frameworks 6)

`networkmanager-qt` 是 KDE Frameworks 6 对 **NetworkManager 客户端库 libnm** 的
Qt 绑定。它提供 `libKF6NetworkManagerQt.so` 与 camel-case 头
（`#include <NetworkManagerQt/Manager>`、`<NetworkManagerQt/ConnectionSettings>`、
`<NetworkManagerQt/WirelessSetting>`、`<NetworkManagerQt/SecretAgent>` 等），
把 NetworkManager 的 D-Bus API 包装成 Qt 风格的 `NetworkManager::` 命名空间。

主要用途：桌面环境的网络管理前端（连接/设备/无线网络/安全设置/VPN、密码
`SecretAgent` 等）。本仓引入它是为了满足 openKylin `kylin-nm-plugin` 依赖链——
`kylin-nm-base`（以及 `kylin-keyring`）的 `.pro` 使用
`INCLUDEPATH += /usr/include/KF6/NetworkManagerQt` 与 `LIBS += -lKF6NetworkManagerQt`。

## 功能概述

- `NetworkManager::Manager` / `Device` / `WiredDevice` / `WirelessDevice` 等：
  遍历设备、激活/断开连接、监听状态变化。
- `NetworkManager::ConnectionSettings` + 全部 `NetworkManager::Setting` 子类
  （IPv4/IPv6/VPN/802.1x/WireGuard/Wireless/...）：连接的序列化/反序列化。
- `NetworkManager::SecretAgent`：实现 NetworkManager 的密钥代理（密码/密钥环）。
- QML 模块 `org.kde.networkmanager`（`networkmanagerqtqml`）。

## OHOS 适配

- **Qt6DBus 来源**：本仓 `qtbase/6.11.1` 以 `FEATURE_dbus=OFF` 构建（不含
  Qt6DBus），必须改用 `qtbase-sql-dbus/6.11.1`；Qt6 Qml/QmlModels 由
  `qtdeclarative/6.11.1` 经 Qt 官方 `QT_ADDITIONAL_PACKAGES_PREFIX_PATH`
  钩子提供。
- **dbus 版本统一**：`libnm/1.58.0` 钉 `dbus/1.14.10.2`，而已发布的
  `FEATURE_dbus=ON` Qt6 包钉 `dbus/1.14.10`，配方用
  `requires("dbus/1.14.10", override=True)` 统一（代价：libnm 按 1.14.10 重建）。
- **libnm 头路径**：配方给生成的 `libnm.pc` 追加 `-I<prefix>/include`，因为
  上游同时用 `<libnm/NetworkManager.h>` 与 `<NetworkManager.h>` 两种拼写。
- **ECM/qtpaths**：configure 期需 `qtpaths`，沙箱需前置 `/system/lib64`
  以取到兼容的 `libc++_shared.so`（bluez-qt 6.28.0 先例）。
- **无源码补丁**：`patches: {}`。
- **已知限制**：40 项上游 ctest 中 37 项通过；3 项依赖 D-Bus *session* 总线的
  集成测试在本沙箱不可运行（AF_UNIX bind 被拒，TCP+ANONYMOUS 总线 QtDBus 用不了）。
  逐项原因见 `6.26.0/test_package/MANIFEST.yml`。

## 依赖关系

- 编译/运行依赖：
  - `qtbase-sql-dbus/6.11.1`（Qt6 Core / Network / DBus）
  - `qtdeclarative/6.11.1`（Qt6 Qml / QmlModels）
  - `libnm/1.58.0`（NetworkManager 客户端库；传递 glib/expat/dbus/libndp/libudev-zero/uuid）
- 构建工具：`ecm/6.26.0`（extra-cmake-modules，`tool_requires`）
- 测试工具：`dbus/1.14.10.2`（build-context `tool_requires`，提供 session bus daemon）

## 消费者接口

| 形式 | 名称 |
|------|------|
| 库 | `libKF6NetworkManagerQt.so` |
| CMake 目标 | `KF6::NetworkManagerQt`（`find_package(KF6NetworkManagerQt)`） |
| pkg-config | `KF6NetworkManagerQt`（**upstream 不提供 .pc，本配方补装**） |
| 头文件目录 | `include/KF6/NetworkManagerQt` |

运行时需 `LD_LIBRARY_PATH` 指向包的 `lib/`（OHOS musl 不解析 RUNPATH）。

## 参考资料

- 上游仓库：https://invent.kde.org/frameworks/networkmanager-qt
- 源码发布：https://download.kde.org/stable/frameworks/
- libnm（NetworkManager）：https://gitlab.freedesktop.org/NetworkManager/NetworkManager
