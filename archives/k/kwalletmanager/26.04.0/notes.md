# kwalletmanager 26.04.0 适配笔记

## 上游
- https://invent.kde.org/utilities/kwalletmanager（KDE Gear release-service）
- 官方源 https://download.kde.org/stable/release-service/26.04.0/src/kwalletmanager-26.04.0.tar.xz
- sha256=fbeba153744b653d255d3a814f04e8702b2fb0e58f646ecd0212868fde262141
- Qt6 Core/Gui/Widgets/DBus + KF6（Archive/Config/ConfigWidgets/CoreAddons/DBusAddons/I18n/KCMUtils/KIO/Wallet/WindowSystem/XmlGui/Crash/StatusNotifierItem/Service）+ ECM
- 产物：kwalletmanager5 可执行（密码管理器 GUI）+ 可选 KCM 模块/KAuth helper（本适配关闭）

## W0 依赖核验（2026-10-01 实测）
- 制品仓 conan list/download 逐项核验：karchive 6.18.0✅ kconfig 6.18.0✅ kconfigwidgets 6.18.0✅ kcoreaddons 6.18.0✅ kcrash 6.18.0✅ kdbusaddons 6.18.0✅ ki18n 6.18.0✅ kservice 6.18.0✅ kwallet 6.18.0✅（仅有 6.18 线）kwindowsystem 6.18.0✅ kxmlgui 6.18.0✅ ecm 6.26.0✅ qtbase 6.11.1/6.11.1.2✅
- **版本线错位（非缺件）**：kio（仅 6.14.0/6.26.0）、kstatusnotifieritem（仅 6.26.0）、kcmutils（仅 6.26.0）——三者均无 6.18 线 binary。kwallet 是本应用核心依赖且仅发布 6.18.0，整图必须锚定 6.18 线 → 上述三件按 kgoldrunner 26.04.0 KIO-trim 先例裁剪。缺件数 0（≤2），不断链。
- **Qt 锚点**：qtbase/6.11.1 的 binary 为 FEATURE_dbus=OFF（无 Qt6::DBus/qdbusxml2cpp，本应用必需 DBus）；qtbase-sql-dbus/6.11.1 带完整 DBus 模块且正是 kwallet/6.18.0 的锚。解法照 kio-kwallet/6.28.0 先例：直接 requires qtbase-sql-dbus/6.11.1，其余 KF6 6.18 保持自然锚 qtbase/6.11.1，两包共存一图不改任何 package_id。**反例已验证**：libkgapi 式 force=qtbase/6.11.1.2 会改变全部 KF6 package_id→binary 全失配→源码重建→kcoreaddons 测试套在沙箱超时失败，不可走。

## 关键决策
1. **KIO 裁剪**（patches/0001）：上游 5 处调用（kwalleteditor.cpp 3 处 storedGet/storedPut、allyourbase.cpp 2 处 storedGet、kwalletmanager.cpp 1 处 CommandLauncherJob），全部作用于本地文件（QFileDialog/drag-drop 选择的 QUrl）→ 等价替换 QFile 直接读写 / QProcess::startDetached。
2. **StatusNotifierItem 可选化**：find_package 降 OPTIONAL_COMPONENTS；`#ifndef KWM_TRIM_SNI` 守卫托盘代码，未找到时目标定义 KWM_TRIM_SNI，托盘分支全跳过、始终窗口模式运行（上游 Launch Manager=false 路径的既有行为）。
3. **KCMUtils+KAuth 裁剪**：src/konfigurator（KCM 模块+KAuth helper）通过 ENABLE_KAUTH=OFF 整目录跳过（上游自带开关）。
4. **kdoctools 裁剪**：BUILD_DOC 门槛改为 `BUILD_DOC AND KF6DocTools_FOUND` + CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=TRUE（kgoldrunner/audiocd 先例）。
5. **N=0 补偿测试**：上游 0 注册测试（无 tests//autotests//add_test，grep 证据）。test_package 三段消费者验证：①安装的 kwalletmanager5 --version/--help 真跑（offscreen）②安装元数据契约核验（desktop/appdata/dbus service/logging categories 文件存在+关键行）③KDEInstallDirs 布局核验。

## 配方要点
- package_type="application" + 上级 commands.json type=tool（kgoldrunner 先例）
- qtbase-sql-dbus/6.11.1 为 Qt6 锚（完整 DBus 模块+qdbusxml2cpp，kwallet 闭包一致；其余 KF6 6.18 自然锚 qtbase/6.11.1 共存，kio-kwallet 先例）
- KF6 6.18 线全部 requires 精确对齐 kwallet/6.18.0 binary closure
- ecm/6.26.0 tool_requires（ECM 模块对 6.18 KF6 线向后兼容，kio/kgoldrunner 先例）
- KF_IGNORE_PLATFORM_CHECK=TRUE + KF_SKIP_PO_PROCESSING=ON（audiocd 先例；ki18n/6.18.0 配方已把 Gettext 降 QUIET）
- ENABLE_KAUTH=OFF + CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=TRUE
- -Wl,-z,max-page-size=0x1000（OHOS lld 布局 workaround，audiocd 先例）
- qt_add_dbus_interface 所需 kf6_org.kde.KWallet.xml 已确认在 kwallet/6.18.0 包 share/dbus-1/interfaces/（KF6WalletConfig.cmake 导出 KWALLET_DBUS_INTERFACES_DIR）
- cmake_find_mode=none 的 qtbase/KF6 包：手工 conan_cmakedeps_paths.cmake（audiocd/libkgapi 先例）
- 运行环境：QT_QPA_PLATFORM=offscreen + HOME/XDG 隔离（kirigami-addons/audiocd 先例）；KF6Wallet DT_NEEDED 相对路径靠 LD_LIBRARY_PATH 前置

## 上游测试（N=0）
- grep -rn 'add_test|enable_testing|ECMAddTests' 全 tarball 无匹配
- 无 tests/ autotests/ 目录
- 消费者测试补偿：kwalletmanager_consumer_test（三段式，见 test_package/MANIFEST.yml）

## 运行时注意（测试）
- KWallet::Wallet 调用 kwalletd5 D-Bus 服务；consumer test 不连 wallet 服务，只验证二进制可执行（--version/--help 走 KAboutData 路径不触 wallet）与安装契约
- kwalletmanager5 无 wallet 后端时会弹 KMessageBox 询问启用——避免交互：不传位置参数/不进主循环，--version/--help 均安全退出
