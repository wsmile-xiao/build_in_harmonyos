# kgoldrunner 26.04.0 适配笔记

## 上游
- https://invent.kde.org/games/kgoldrunner tag v26.04.0（release-service tarball）
- 官方源 https://download.kde.org/stable/release-service/26.04.0/src/kgoldrunner-26.04.0.tar.xz
- sha256=375fca9618287cd884fb3bb824ece47c28c41b2b3c04dd7362a144ef74fb829d（与 pipeline.md 记录一致）
- Qt6 Gui+Widgets + KF6（Config/ConfigWidgets/CoreAddons/Crash/DBusAddons/DocTools/I18n/KIO/WidgetsAddons/XmlGui/IconThemes）+ KDEGames6

## 关键决策
1. **KIO 裁剪**（patches/0001）：上游仅一处 KIO::mkpath（创建用户关卡目录）。kio/6.26.0 的 binary 锚定 KF6 6.26 线，与 libkdegames/26.04.0 binary 的 6.18 线不兼容（conan list 实测：混线导致所有 KF6 package id 变化、无 prebuilt binary）。单点调用等价替换 QDir().mkpath()（创建目录+缺失父目录，已存在返回 true）。pipeline.md 原记录"kio/6.26+6.18 无冲突"仅在配方解析层成立，binary 层失配。
2. **kdoctools 裁剪**：文档工具链不在平台包集（audiocd 26.04.3 先例），doc/ 与 kdoctools_install(po) 移出构建；CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=TRUE。
3. **KF6 6.18 线**：全部 KF6 requires 与 libkdegames/26.04.0 binary closure 逐一对齐（kconfig/kconfigwidgets/kcoreaddons/kcrash/kdbusaddons/ki18n/kwidgetsaddons/kxmlgui/kiconthemes 6.18.0）。
4. **N=0 补偿测试**：上游 0 注册测试（无 tests//autotests//add_test，grep 证据）。test_package 三段消费者验证：①执行安装的 kgoldrunner --version（offscreen）②解析全部 gamedata game_*.txt（G 头/L 标记/28x20 网格契约——src/kgrgameio.cpp 运行时消费的真实数据）③深度校验 level 1 网格几何。

## 配方要点
- package_type="application" + commands.json（klystrack 先例）
- ecm/6.26.0 tool_requires（ECM 模块对 6.18 KF6 线向后兼容，kio 6.26 先例）
- KF_IGNORE_PLATFORM_CHECK=TRUE + KF_SKIP_PO_PROCESSING=ON（audiocd 先例）
- -Wl,-z,max-page-size=0x1000（OHOS lld 布局 workaround，audiocd 先例）
- cmake_find_mode=none 的 qtbase/KF6 包：手工 conan_cmakedeps_paths.cmake（audiocd/libkcddb 先例）
- 运行环境：QT_QPA_PLATFORM=offscreen + HOME 隔离（kirigami-addons/audiocd 先例）

## 上游测试（N=0）
- grep -rn 'add_test|enable_testing|ECMAddTests' 全 tarball 无匹配
- 无 tests/ autotests/ 目录
- 消费者测试补偿：kgoldrunner_consumer_test（三段式，见 test_package/MANIFEST.yml）
