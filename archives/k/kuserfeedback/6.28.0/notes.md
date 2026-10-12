# kuserfeedback 6.28.0 适配笔记

## Scope

kuserfeedback 是 KDE Frameworks 6 的用户反馈/遥测与问卷框架
（libKF6UserFeedbackCore / libKF6UserFeedbackWidgets / KF6UserFeedbackQml），
是 KDE Gear 应用（如 Elisa、Kate 等）依赖统计与问卷投放的基础设施。
ohpcd 制品仓此前未发布该包，按 R36 依赖优先原则适配本包。

## 上游测试三步法（R51）

1. 清点（N 口径，rule4 按上游构建系统注册数）：
   - autotests/CMakeLists.txt 通过 uf_add_test()（内部 add_test）注册。
   - **无条件注册 6 个**：datasourcetest、openglinfosourcetest、providertest、
     selectionratiosourcetest、surveyprovidertest（链 KF6UserFeedbackCore+Qt6::Gui）、
     feedbackconfigtest（链 KF6UserFeedbackWidgets）。
   - **条件注册 1 个**：surveytargetexpressiontest（HAVE_SURVEY_TARGET_EXPRESSIONS，
     即 FLEX+BISON 找到时；本配方 ENABLE_SURVEY_TARGET_EXPRESSIONS=ON 且 OHOS SDK
     自带 flex 2.6.4/bison 3.8.2，注册成立）。
   - Console 门控 10 个（producttest/schematemplatetest/sampletest/serverinfotest/
     schemamodeltest/datamodeltest/timeaggregationmodeltest/categoryaggregationmodeltest/
     numericaggregationmodeltest/ratiosetaggregationmodeltest）：TARGET
     KF6UserFeedbackConsole 为假（ENABLE_CONSOLE=OFF，Qt6Charts 未发布 ohpcd），
     不注册、不参与 N。
   - PHP 门控 14 个（productapitest/productmodeltest/surveyapitest/submittest +
     7 个 PHPUnit 目标 + php_lint）：ENABLE_PHP=OFF（OHOS 无 PHP 服务栈，
     server/testserver 不构建），不注册、不参与 N。
   - tests/ 目录 3 个 exe（feedbackconfigwidgettest/notificationpopuptest/orwell）
     无 add_test 注册，仅为手工 demo，不参与 N。
   - **申报 N = 7**（6 无条件 + 1 flex/bison 条件达成）。
2. 运行：BUILD_TESTING=ON 真机构建，ctest --output-on-failure，
   QT_QPA_PLATFORM=offscreen + 隔离 HOME/XDG_RUNTIME_DIR +
   KUSERFEEBACK_SKIP_TESTOPENGLINFOSOURCE=1（上游自带 WIN32 同款豁免开关，
   headless OHOS 无 GL）。实测结果回填本文件与 PR 正文。
3. 回填：见 manifest.yaml / test_package/MANIFEST.yml（CI 构建号后补）。

## Adaptations

- 0001-lower-ecm-version.patch：上游 find_package(ECM ${KF_DEP_VERSION}) 即
  6.28.0，registry KF6 代 ECM 最新为 6.26.0 → 降版（attica/6.28.0、
  kdnssd/6.29.0 同款先例）。
- 0002-disable-po-qm-processing.patch：注释顶层 ecm_install_po_files_as_qm(poqm)
  （140 个上游 .po 需 Qt6LinguistTools，ohpcd 未发布）；KF_SKIP_PO_PROCESSING=ON
  双保险。ECM 6.26.0 实测 ecm_create_qm_loader 仅 configure_file 自包含
  loader 桩（无 LinguistTools 依赖），src/provider/core/CMakeLists.txt 第 1 行
  的调用保留不动。
- KF_IGNORE_PLATFORM_CHECK=TRUE：OHOS 不在 KDE 平台白名单。
- ENABLE_PHP=OFF / ENABLE_PHP_UNIT=OFF：server 端（Elasticsearch/PHP）全关，
  不进入构建。
- ENABLE_DOCS=OFF：qdoc 属 Qt6ToolsTools（未发布），且 ecm_generate_qdoc
  找不到工具时本就静默跳过，显式关闭防 find_package 噪音。
- ENABLE_CONSOLE=OFF：UserFeedbackConsole/CLI 需 Qt6Charts（未发布）；
  provider 库不受影响。
- ENABLE_SURVEY_TARGET_EXPRESSIONS=ON：OHOS SDK 自带 flex/bison 可用，
  保留问卷目标表达式能力。
- ECM_MODULE_PATH 手工注入（CMakeDeps 生成的 ECMConfig.cmake 不传播该变量），
  同 kstatusnotifieritem/6.26.0 模式。
- conan_cmakedeps_paths.cmake 手工生成：qtbase/qtdeclarative 的
  package_info 均为 cmake_find_mode=none，CMakeDeps 不会替我们把它们的
  lib/cmake 加进 CMAKE_PREFIX_PATH。

## 依赖选型说明

- qtbase/6.11.1（vanilla，非 qtbase-sql-dbus 变体）：server 全关后本包
  无 Qt6::Sql/Qt6::DBus 引用（src/ 全树 grep 实测为空），vanilla 已含
  Core/Network/Gui/Widgets/Test（recipe FEATURE_network/widgets/testlib=ON）。
- qtdeclarative/6.11.1：KF6UserFeedbackQml 模块（Qt6::Qml）需要；其自身
  requires qtbase/6.11.1（vanilla），依赖树单一 qtbase 无变体冲突
  （akonadi/25.12.3 已实证 qtdeclarative 与 qtbase-sql-dbus 共存路径，
  本包更简单——全树只有一个 qtbase 变体）。

## Verification

- 源码 SHA256：`07f279845b3cd6e675513afb81f3c6274b2f6757edc149d163116b3c50dfa0df`
  （下载实测；注意 KDE 源布局为 stable/frameworks/6.28/ 次版本目录，
  6.28.0/ 目录 404）。
- 依赖：qtbase/6.11.1、qtdeclarative/6.11.1（均已在 ohpcd 发布，conan
  download 实测）；tool_requires ecm/6.26.0（同实测）。
- 上游测试：N=7，ctest 实测结果（通过率）在 PR 正文按实测口径申报。
- test_package：链接 KF6::UserFeedbackCore，6 项断言（productIdentifier /
  telemetryMode 默认值+set 往返 / submissionInterval / surveyInterval /
  dataSource 未知 id 返回 nullptr）。

## Notes

- 本包为库类型（package_type=library），无 commands.json（R38 不适用）。
- 下游 KDE Gear 应用（Elisa 等）可直接
  `self.requires("kuserfeedback/6.28.0")`。
- qml 模块（KF6UserFeedbackQml）随包构建；QML 插件运行需 qtdeclarative
  在环境内，消费者 conan install 自动静态带上。

---

**编译结束**: 2026-10-05
**最终状态**: built
