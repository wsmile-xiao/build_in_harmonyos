# kcmutils 6.26.0 适配笔记

## 编译环境
- 构建系统: cmake (ECM)
- 编译日期: 2026-09-19
- 编译器: clang/clang++ 15 (OHOS SDK, aarch64-linux-ohos)
- 状态: built
- worktree: ~/huawei/worktrees/j669539/kcmutils-6.26.0

## 软件简介

kcmutils 是 KDE Frameworks 6 的配置模块工具库：KCMultiDialog（多页配置
对话框）、KCModule（配置模块基类）、KCModuleLoader（插件加载）、
KPluginWidget + kcmshell6 运行器。kinfocenter（任务 #12847）的
`find_package(KF6 COMPONENTS KCMUtils ...)` 即本件；前序 PR #7445
（6.18.0）stale，本件是 KF6 6.26 线的新适配（任务 #13728）。

## 与 6.18.0 PR #7445 的差异

| # | 变更 | 原因 |
|---|------|------|
| 1 | 依赖矩阵 6.18 → 6.26（kio/kxmlgui/kitemviews 6.26.0） | W0 conan download 核验已发布 |
| 2 | kconfigwidgets 6.18.0 + override=True 顶传递依赖到 6.26 | kconfigwidgets/6.26.0 未发布（kxmlgui 6.26.0 同款方案，任务 #13725 实证） |
| 3 | 补丁 0001：裁 src/qml（kcmutilsqmlplugin）挂 KCMUTILS_BUILD_QML_PLUGIN 开关 | **kio/6.26.0 是 KIOCORE_ONLY 基线**（无 KIOGui/KIOWidgets 目标），而 kcmutilsqmlplugin 链接 KF6::KIOGui |
| 4 | 补丁 0001：autotests 的 qmlkcm fixture + kcmloadtest 同开关裁剪 | kcmloadtest.testLoadQmlPlugin 加载的 QML KCM import org.kde.kcmutils（被裁插件提供） |
| 5 | 补丁 0001：find_package(KF6ConfigWidgets 6.18.0) + KF6KCMUtilsConfig.cmake.in find_dependency 同步降板 | kconfigwidgets cap（kxmlgui 同款两处地板） |
| 6 | BUILD_TESTING=ON + _run_upstream_tests | 6.18 PR #7445 因上游测试未跑而 stale；本机 arm64 OHOS 可真跑 |
| 7 | qtbase → qtbase-sql-dbus/6.11.1 | 保持 6.18 配方形态（USE_DBUS=OFF 时 DBus 组件仅 kcmshell6 可选路径） |
| 8 | LD_LIBRARY_PATH 前置 /system/lib64 | 沙箱 libc++_shared.so 遮蔽（kconfig 6.26.0 先例） |

## QML 插件裁剪的消费者影响

- 裁掉的 kcmutilsqmlplugin 是 org.kde.kcmutils QML 模块（声明式 KCM
  框架）。KF6KCMUtilsCore / KF6KCMUtilsQuick / KF6KCMUtils 三个库完整保留。
- kinfocenter（本链最终消费者）走 Qt Widgets 路径
  （KPageDialog/KCMultiDialog），不依赖声明式 QML 插件。
- 补丁用 `if(KCMUTILS_BUILD_QML_PLUGIN)` 守卫而非删除——上游源码结构
  可追溯，未来 kio 发布 KIOGui 后可一行开关恢复。

## 上游测试（N 申报口径）

上游 autotests/CMakeLists.txt 在 QML 插件裁剪形态下注册：
- kcmultidialogtest（ecm_add_tests）
- module_data_test（module_data_codegen/ecm_add_test）
- kcmloadtest 依赖 QML 插件（testLoadQmlPlugin 行加载 kcm_testqml），
  与 qmlkcm fixture 一起被 KCMUTILS_BUILD_QML_PLUGIN 开关守卫——
  本形态不注册，豁免原因：kio/6.26.0 KIOCORE_ONLY 无 KIOGui，
  QML KCM 加载链断裂（见 PR 正文豁免段）。

本机（arm64 OHOS）conan create 内 ctest 实跑结果见 reports/。

## 依赖核验（W0，R35 conan download 口径）

qtbase-sql-dbus/6.11.1 ✅ qtdeclarative/6.11.1 ✅ kio/6.26.0 ✅
kxmlgui/6.26.0 ✅（件 1 本机已建，PR #10999 待合入后制品仓可见）
kconfigwidgets/6.18.0 ✅（cap）kitemviews/6.26.0 ✅ openssl/3.5.6.1 ✅
zstd/1.5.7 ✅ libxml2/2.15.3 ✅ ecm/6.26.0 ✅
override 目标：kconfig/kcoreaddons/kguiaddons/ki18n/kwidgetsaddons/
kcolorscheme/kcodecs 全 6.26.0 ✅

## conan override 方案（同 kxmlgui 6.26.0 实证）

- 无 override：`Version conflict: Conflict between ki18n/6.26.0 and
  ki18n/6.18.0 in the graph`
- override 单声明后：graph 解析成功，全图唯一 6.26 版本
- 知识草稿：knowledge/drafts/DRAFT-conan-override-kf-version-conflict.kv/.md
  （件 1 PR #10999 已携带）
