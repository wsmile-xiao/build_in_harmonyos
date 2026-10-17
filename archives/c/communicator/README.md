# communicator

KDE Maui Communicator —— Maui 系列联系人管理桌面应用：浏览/检索联系人、
拨号/发邮件/发短信入口、联系人头像与 vCard 读写，Qt6/QML 实现（MauiKit4）。

## 功能概述

- 联系人列表（列表/网格视图）与联系人详情页
- 从共享 vCard 存储（kpeoplevcard 目录）读取联系人；新增/编辑/删除 vCard
- 消息撰写（SMS/mail 集成入口）、联系人字段快速操作

## OHOS 适配

- Qt6/QML 纯可执行应用（`qt_add_qml_module`，NO_PLUGIN，无库产物），
  Conan 配方按 application 包处理：不声明 `cpp_info.libs`，仅声明 `bin`。
- KPeople 改为可选能力（`find_package(KF6People CONFIG QUIET)` + `HAVE_KPEOPLE`
  编译开关）；无 KPeople 时直接扫描共享 vCard 目录，行为与 KPeople vcard
  后端同源（补丁 `4.0.2/patches/0001`）。
- Qt6::Widgets 为硬依赖：非 Android 入口使用 `QApplication`（勿按 Linux
  GUI 惯例裁掉 Widgets）。
- KDE 平台探测需 `KF_IGNORE_PLATFORM_CHECK=TRUE`（OHOS 不在 KDE 平台列表）。
- 上游声明的 KIO（Core+Gui）与 MauiKit4 FileBrowsing 依赖已裁剪：源码未使用
  KIO 符号，头像文件对话框改用 QtQuick.Dialogs（补丁 `4.0.2/patches/0002`），
  配方仅依赖 MauiKit4 Core。

## 依赖关系

- Qt6 ≥6.5.2：Qml/Quick/QuickControls2（qtdeclarative）、Concurrent/Widgets（qtbase）
- KF6：I18n、CoreAddons、Service、Contacts；（可选）People
- MauiKit4：Core
- 构建工具：CMake ≥3.16、ECM

## 参考资料

- 官网：https://mauikit.org
- 源码：https://invent.kde.org/maui/communicator
- 发布归档：https://download.kde.org/stable/maui/communicator/4.0.2/
