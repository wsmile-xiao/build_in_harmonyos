# qtquicktimeline 6.11.1 适配笔记（HarmonyOS PC / aarch64）

## 概述

- 软件：qtquicktimeline 6.11.1（Qt Quick Timeline 模块，C++/QML）
- 官方源码包：qtquicktimeline-everywhere-src-6.11.1.tar.xz
  - sha256: af53f643fd9e4045e1b9ba919998e5c048ca877452c08036c9c8c5ee07ea8c27
- 构建系统：CMake（Qt 6 模块构建，qt_internal_add_qml_module）
- 依赖：qtbase/6.11.1、qtdeclarative/6.11.1（均为 main 已合入配方）
- 产物：libQt6QuickTimeline.so（动态库，含 QtQuick.Timeline QML 模块，无需 commands.json）

## 适配要点（conanfile.py）

- requirements(): qtbase/6.11.1 + qtdeclarative/6.11.1（模块要求 Qt::Quick 与 Core cbor 特性）
- generate(): OhosLinuxPlatformBlock；CMAKE_PREFIX_PATH=qtbase；
  QT_ADDITIONAL_PACKAGES_PREFIX_PATH=qtdeclarative；QT_QMAKE_TARGET_MKSPEC=harmonyos-clang
- build(): cmake configure/build，随后显式构建并运行 2 个上游 QML 测试
  （tst_qtquicktimeline / tst_blendtrees），offscreen QPA + ctest
- package(): cmake.install() + SONAME 软链修复 + OHOS ELF 重签名（binary-sign-tool）
- package_info(): cmake_find_mode=none，复用 Qt 自带 Qt6QuickTimelineConfig.cmake

## 测试

- 上游测试：tst_qtquicktimeline / tst_blendtrees（2 个 QML 测试）
- test_package：QML 冒烟测试，经 QQmlEngine 加载 import QtQuick.Timeline 6.11
