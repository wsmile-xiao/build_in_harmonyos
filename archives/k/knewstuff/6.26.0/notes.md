# knewstuff 6.26.0 notes（R01）

## Scope

KDE Frameworks 6 KNewStuff（Get Hot New Stuff，网络资源下载/安装），产出 KF6NewStuffCore、
KF6NewStuffWidgets、newstuffqmlplugin 与 knewstuff-dialog6。本版本为 aurorae #3832 依赖链
（KF6NewStuff）补件，配方以 knewstuff/6.29.0（R03-final）为底稿移植。

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE`：绕过 KDE 平台白名单（OHOS 不在列表内）。
- `KF_SKIP_PO_PROCESSING=ON`：跳过翻译目录生成（lconvert 在基线包不可用）。
- `BUILD_TESTING=ON` + ctest 上游测试；`QT_QPA_PLATFORM=offscreen` 无头运行。
- `BUILD_DESIGNERPLUGIN=OFF`（Qt6UiPlugin 未发布）。
- 可选依赖 KF6Kirigami / KF6Syndication 置为未找到（ohpcd 未发布，不进基线包）。
- 补丁 0001：KF_DEP_VERSION 6.26.0→6.18.0（ECM 6.26.0 已发布无需降级——与 6.29.0 底稿
  的差异点：底稿同时降 ECM 6.29.0→6.26.0，本版上游 ECM 要求恰好等于制品仓版本）。
- 补丁 0002/0003：KF6I18nQml 可选化 + QML 上下文替换（KLocalizedQmlContext→QQmlContext）。
- 补丁 0004（R05 可重定位链接）：显式 SONAME + KF6 依赖 -l 裸名 + PRIVATE
  target_link_directories（4 文件：core/widgets/qtquick/dialog）。
- `ECM_MODULE_PATH`、`conan_cmakedeps_paths.cmake` 手工写入（cmake_find_mode=none 的
  qtbase/qtdeclarative/KF6 包不被 CMakeDeps 自动加搜索路径）。
- `generate()` 注入 `KNEWSTUFF_DEP_LIB_DIRS` 与全局 include/lib 路径（R05 配套）。

## Dependencies（对齐制品仓）

qtbase/6.11.1、qtdeclarative/6.11.1、karchive/6.18.0、kconfig/6.18.0、kcoreaddons/6.18.0、
ki18n/6.18.0、kpackage/6.18.0.1、kwidgetsaddons/6.18.0、attica/6.28.0、build: ecm/6.26.0。
全部 conan download --only-recipe 实测存在（2026-09-07）。

## Upstream tests（实测）

上游 tarball 解压后逐目录统计：autotests/knewstuffentrytest.cpp（1）+
autotests/core/{knewstuffauthortest,knewstuffenginetest,installationtest,atticaprovidertest}
（4）= 5 个测试源文件。ctest 注册层面：atticaprovidertest 受上游 `if(LINUX)` 门控，
OHOS 构建注册 4 个（knewstuffentrytest/knewstuffauthortest/knewstuffenginetest/installationtest），
与 6.29.0 适配的 4/4 一致。
