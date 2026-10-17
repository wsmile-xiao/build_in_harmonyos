# pimcommon 25.12.3 OHOS PC 适配笔记

## 基本信息

- 软件名称: pimcommon（KDE PIM 公共组件库，核心库 KPim6PimCommon）
- 版本: 25.12.3（KDE release-service，PIM_VERSION 6.6.3）
- 构建系统: cmake + ECM + Qt6/KF6
- 编译日期: 2026-09-19
- 状态: built（conan create 全绿：上游 22/22 + test_package 1/1）
- 上游: https://invent.kde.org/pim/pimcommon（tag v25.12.3 实证 94d96309）
- 源码包: https://download.kde.org/Attic/release-service/25.12.3/src/pimcommon-25.12.3.tar.xz
  （sha256 6496e293294e23c6db8a19e4774313426bcdc8478defb2141ec4f6653f9f4b2f）

## 适配策略（core-library-only port）

上游 pimcommon 构建三个库：pimcommon（核心）、pimcommonakonadi、pimcommon-activities。
后两者深度依赖未发布到 ohpcd 制品仓的 KPim6 栈（Akonadi/AkonadiContactWidgets/
KIMAP/KLdapWidgets/Libkdepim/KCMUtils/AkonadiSearch/PlasmaActivities），本适配只构建
核心库 KPim6PimCommon（KDE PIM 链基础组件先落地的打法，同 libkdepim 25.12.3 先例）。

### 依赖基线选择（全 6.14.0 线）

- qtbase-sql-dbus/6.11.1：核心库 PUBLIC 链接 Qt::DBus（imap resource settings D-Bus
  接口），普通 qtbase/6.11.1 是 FEATURE_dbus=OFF（E323），必须用带 DBus 的变体
  （akonadi 25.12.3 先例）。qtbase-sql-dbus 的 conan 包目录在 CMAKE_PREFIX_PATH 中
  优先，普通 qtbase 被 skip。
- kio/6.14.0：完整形态（KIOCore+KIOGui+KIOWidgets，实测包内含 libKF6KIOWidgets.so
  与 KF6::KIOWidgets imported target）；6.26.0 是 KIOCORE_ONLY 无 KIOWidgets。核心库
  PRIVATE 链接 KF6::KIOWidgets（renamefiledialog / needupdateparsehtmljob 用
  KIO::StatJob / KIO::TransferJob）。
- 其余 KF6 全 6.14.0 线（kcodecs/kcolorscheme/kconfig/kcoreaddons/ki18n/kitemviews/
  kjobwidgets/kwidgetsaddons/kxmlgui），与 kio/6.14.0 的传递依赖完全同版本，无冲突
  （keditbookmarks 26.04.0 先例同款基线）。
- libxml2/2.15.3：SDK lld 链接期需要 libxml2.so.16（E132，kio 6.14.0 配方先例）。

### patch（0001-ohos-adaptation.patch）内容

1. 顶层 CMakeLists：剔除未发布依赖的 find_package（KF6Archive/KF6Contacts/
   KF6ItemModels/KF6KCMUtils/KF6NewStuff/KF6Purpose/KF6Service/KPim6 全家/
   KF6TextAddons 三件套/PlasmaActivities/akonadi-search 块）；KF_MIN_VERSION 降到
   6.14.0 匹配制品仓基线。
2. src/CMakeLists：只 add_subdirectory(pimcommon)（pimcommonakonadi/
   pimcommon-activities 整库剔除）。
3. src/pimcommon/CMakeLists：剔除 add_resource_iface（akonadi kcfg2dbus 宏 +
   xsltproc，只服务已剔除的 pimutil::createImapSettingsInterface）；target_link_
   libraries 剔除 TextCustomEditor/TextAutoCorrectionWidgets/NewStuffCore/
   NewStuffWidgets/Purpose/PurposeWidgets（核心库保留 KIOCore/KIOWidgets/I18n/
   XmlGui/ItemViews/Codecs/ColorScheme/WidgetsAddons）。
4. 源码降级重写（保留公共 API，OHOS 平台退到 Qt 基础控件，头注释注明原因）：
   - SpellCheckLineEdit：TextCustomEditor::RichTextEditor → QPlainTextEdit
   - TemplateEditDialog：TextCustomEditor::PlainTextEditorWidget → QPlainTextEdit
   - LineEditWithAutoCorrection：autocorrection 变为 no-op（保留
     setAutocorrectionLanguage API）
   - PurposeMenuWidget：Purpose::Menu → 空 QMenu（保留 menu() API 与 objectName）
   - TemplateListWidget::slotContextMenu：剔除 KNSWidgets::Action 菜单项
     （KF6NewStuff 未发布且 OHOS 无 GHNS 服务）
   - pimutil：剔除 createImapSettingsInterface（消费者只在 pimcommonakonadi）
5. KPimCommonConfig.cmake.in：find_dependency 与实际 link interface 对齐
   （Qt6 Widgets/DBus/Gui + KF6Codecs/ColorScheme/Config/I18n/ItemViews/KIO/
   WidgetsAddons/XmlGui），剔除 TextAddons 依赖。
6. 测试目录：autocorrection/autotests 与 autocorrection/tests 的 CMakeLists 清空
   （lineeditwithautocorrectiontest 深度依赖 TextAutoCorrectionCore API；
   autocorrection 在本平台是文档化 no-op）。其余 22 个上游测试全部保留注册。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|---------|
| 1 | ECMQueryQt 执行 qtpaths 报 symbol not found | 沙箱 LD_LIBRARY_PATH 里 /data/storage/el1/bundle/libs/arm64 的不兼容 libc++_shared.so 影子 | _build_runtime_env 用 Environment.prepend_path 把 /system/lib64 与 SDK llvm/lib（含 aarch64-linux-ohos 子目录）前置，build() 用 .vars().apply() 包裹 cmake（kconfig/kcrash 6.26 先例） |
| 2 | CMake TryCompile 阶段 lld 报 libxml2.so.16 not found | SDK lld 依赖 libxml2.so.16 | 声明 libxml2/2.15.3 并注入其 lib 目录到 LD_LIBRARY_PATH（E132） |
| 3 | test_package 阶段 KF6::I18n 等 target not found | KPimCommonConfig.cmake.in 的 find_dependency 不全（QCH 生成的 INTERFACE link 含全部 PRIVATE 依赖） | patch 补全 8 个 KF6 find_dependency |
| 4 | 上游测试 ctest 全挂：`../../bin/libKF6ConfigCore.so` 加载失败 | 已发布 KF6 包带 build-tree 相对 DT_NEEDED，musl loader 按 cwd 解析 | _prepare_upstream_test_links 在每个 CTestTestfile.cmake 目录的 ../bin ../../bin ../../../bin ../../../../bin 建 symlink 农场（keditbookmarks 26.04.0 先例） |
| 5 | ctest 测试进程 QOffscreenPlatformPlugin 找不到 | QT_PLUGIN_PATH 未指向 qtbase 包 | _build_runtime_env 注入每个依赖包的 plugins 与 lib/plugins 目录 |
| 6 | knewstuff 引入 karchive/6.18 与 6.14 冲突 | knewstuff 全系列配方要求 6.18 系 | 剔除 knewstuff 依赖（核心库仅用于"下载新模板"菜单项，OHOS 无 GHNS） |

## 测试统计（申报口径）

- **上游注册测试数 N = 22**（BUILD_TESTING=ON 时 src/pimcommon 各 autotests 目录
  ecm_add_test/add_test 实际注册：widgets 3 + shareserviceurl 1 + customtools 1 +
  autotests 2 + configureplugins 2 + genericplugins 3 + needupdateversion 5 +
  whatsnew 5；autocorrection/autotests 的 1 个因 TextAddons 剔除未注册——归入
  "上游测试用例减少原因"段申报）。
- 实测执行 22 个，22 通过，0 失败（**100%**）。
- test_package（消费者测试，鸿蒙特有）：1/1 通过（100%）——链接 KPim6PimCommon 并
  调用公共 API（Util::isImapResource/generateEmailList、NetworkManager 构造、
  OHOS 降级控件 SpellCheckLineEdit/PurposeMenuWidget 行为验证）。

## 与上游对比的测试减少说明

- pimcommonakonadi 的 19 个测试（acl 2 + addressline 6 + blacklist 5 + collectionpage
  2 + folderdialog 1 + ldap 1 + 其他）与 pimcommon-activities 的测试随库整体剔除
  （依赖未发布的 KPim6 栈）。
- autocorrection/autotests/lineeditwithautocorrectiontest：深度依赖
  TextAutoCorrectionCore API（KF6TextAddons 未发布），归入减少原因。

**编译结束**: 2026-09-19 15:50
**最终状态**: built
