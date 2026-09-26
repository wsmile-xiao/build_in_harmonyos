# isoimagewriter

KDE Gear 的 ISO 镜像写入工具（"ISO Image Writer"）：把下载好的 ISO 镜像写入 U 盘，
写完后回读校验写入结果。Qt 6 Widgets / KF6 桌面应用。

- 上游: https://invent.kde.org/utilities/isoimagewriter
- 归档源: https://download.kde.org/stable/release-service/26.04.0/src/isoimagewriter-26.04.0.tar.xz
- 版本: 26.04.0（KDE Gear 26.04.0）
- License: GPL-3.0-or-later

## 产物

- `bin/isoimagewriter` — 主程序（Qt6 Widgets，Qt6::DBus 经 UDisks2 枚举可移动盘，
  KF6::Solid 监听设备插拔）
- `share/applications/org.kde.isoimagewriter.desktop`
- `share/metainfo/org.kde.isoimagewriter.appdata.xml`
- `share/icons/hicolor/scalable/apps/org.kde.isoimagewriter.svg`

## OHOS 适配（26.04.0）

| 文件 | 说明 |
|------|------|
| `26.04.0/conanfile.py` | Conan 配方（CMake + ECM + Qt6/KF6 应用包打法） |
| `26.04.0/conandata.yml` | 官方 tarball URL + SHA256 + 补丁清单 |
| `26.04.0/patches/0001-isoimagewriter-CMakeLists.txt.patch` | 让 HarmonyOS 走 Linux 分支（平台源码与 desktop/appdata 安装规则） |
| `26.04.0/test_package/` | 消费者验证：离屏执行 `bin/isoimagewriter --version` / `--help` |
| `commands.json` | 软件级命令行声明（R38，application 包必需） |

关键点：

- OHOS Conan 工具链把 `CMAKE_SYSTEM_NAME` 设为 `HarmonyOS`，上游只在
  `Windows / Linux / FreeBSD` 三分支里挂平台源码，会落进 `else()` 丢掉
  `platform_lin.cpp` / `usbdevicemonitor_lin.cpp` / `externalprogressbar_lin.cpp`
  → 链接缺符号。补丁把 `HarmonyOS` 并入 Linux 分支（**不引入任何平台宏**）。
- 上游 `Gpgmepp` / `QGpgmeQt6` 是**可选**依赖（`find_package` 无 `REQUIRED`）。
  制品仓的 gpgmepp 1.23.2 未启用 Qt6 binding，因此构建的是上游自带的非 GPG
  变体（`_USE_GPG` 未定义），ISO 签名校验功能不可用——这是上游支持的配置组合，
  非空壳实现。
- 需要 `Qt6::DBus`，故依赖 `qtbase-sql-dbus/6.11.1`（`FEATURE_dbus=ON`），
  而非 `FEATURE_dbus=OFF` 的 `qtbase/6.11.1`。

适配详情见 `26.04.0/notes.md`。
