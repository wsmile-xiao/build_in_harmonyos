# kjumpingcube

KJumpingCube 是 KDE 出品的回合制策略棋类游戏（KDE release-service
26.04.0）：玩家与 AI（Kepler/Newton 对手引擎）交替占领/引爆立方格，占领
全部棋盘者获胜。基于 KXmlGui 框架的 GUI 应用，上游仅产出单个可执行文件
`bin/kjumpingcube` 与数据文件（主题 SVG、桌面文件、图标、手册文档）。

## 功能概述

- 单人对抗 AI（可配置三档难度与两种对手引擎）或本地双人对战
- SVG 主题（themes/default.svg，gzip 压缩安装）
- KConfig 持久化设置（kjumpingcube.kcfg）、KXmlGui 菜单/工具栏 XML UI
- KCrash 崩溃处理、KDBusService 单实例 DBus 注册

## OHOS 适配

- `KF_IGNORE_PLATFORM_CHECK=TRUE` 绕过 KDE 平台白名单。
- `KF_SKIP_PO_PROCESSING=ON` 跳过翻译目录处理。
- KF6DocTools 在 ohpcd 无 6.18.0 版本：手册文档（doc/）经 patch 移除，
  不参与构建与安装。
- KIO 在 ohpcd 无 6.18.0 版本：以 kio/6.14.0 消费（game.cpp 经
  KIO::stat/KIO::file_copy 实现 URL 保存/加载），并将其 6.14 依赖族
  override 钉到统一的 6.18.0 家族（KF6 大版本内 ABI 稳定）。
- Qt6::DBus 由 `qtbase-sql-dbus/6.11.1` 变体提供（E323/E441），并在
  CMake 搜索路径中确定性置首。
- 依赖 `libkdegames/26.04.0.1`（SONAME 修复版；官方 26.04.0 为缺陷版）。
- 构建产物 DT_NEEDED 路径形态条目在 package() 内清洗为 basename 并重
  签名（E537 惯用法，禁用 patchelf）。
- 上游无测试套件（NO_UPSTREAM_TESTS）：test_package 以无头
  （offscreen Qt）方式真实执行 `bin/kjumpingcube --version` 并断言产物
  DT_NEEDED 的 OHOS 可移植性（无路径形态条目、libKDEGames6 在列）。

## 依赖关系

- 运行/链接：qtbase-sql-dbus/6.11.1（Qt6 Widgets/Svg/DBus）、
  qtsvg/6.11.1、KF6 6.18.0 家族（kconfig/kconfigwidgets/kcoreaddons/
  kcrash/kdbusaddons/ki18n/kjobwidgets/kxmlgui/kwidgetsaddons/
  kiconthemes 及其传递依赖）、libkdegames/26.04.0.1
- 构建：ecm/6.26.0（tool_requires）、clang（OHOS NDK 工具链）
- 上游声明但适配后不再需要：KF6DocTools（文档，doc/ 手册经 patch 移除）

## 参考资料

- 主页：https://apps.kde.org/kjumpingcube
- 源码：https://invent.kde.org/games/kjumpingcube
- 发布归档：https://download.kde.org/stable/release-service/26.04.0/src/kjumpingcube-26.04.0.tar.xz
