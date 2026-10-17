# kirigami-addons 1.13.0 适配笔记

## Scope

QML addon 插件库（KDE kirigami-addons），为 Kirigami 应用提供 formcard/settings/
treeView/delegates 等 convergent QML 组件。平台任务 #6387（依赖项活动，j669539）。

任务提示的"qtbase 裁剪包无 Qt6Qml"风险已被 W0 实测推翻：Qt6Qml/Quick/
QuickControls2/QuickEffects 组件由独立发布的 qtdeclarative/6.11.1 提供
（conan download + conan install 二进制双实证，R35 口径），kirigami/6.18.0
本体也已在仓。结论：可行，无依赖缺口。

## 编译环境

- 构建系统: cmake (ECM/KDE, ecm_add_qml_module 全家桶)
- 编译日期: 2026-09-07
- 编译器: clang/clang++ 15.0.4 (OHOS SDK, aarch64-linux-ohos)
- 状态: built (conan create 全绿, test_package 1/1 PASS)

## 依赖版本（全部 conan download -r=ohpcd 实测在仓）

- qtbase-sql-dbus/6.11.1, qtdeclarative/6.11.1, qtsvg/6.11.1,
  qtshadertools/6.11.1, qtmultimedia/6.11.1
- kirigami/6.18.0 (KF6::Kirigami + org.kde.kirigami QML 模块)
- ki18n/kconfig/kcoreaddons/kguiaddons/kcolorscheme/kcrash 6.18.0,
  kiconthemes 6.18.0.1
- ecm/6.26.0 (tool_requires)

**唯一禁用项**: kglobalaccel（6.14/6.18/6.26 全版本不在仓，conan download
实测 "system acceleration policy not enabled" = 配方缺失）。上游
keysequencehelper.cpp 有 `#elif defined(HAVE_KGLOBALACCEL)` 优雅降级路径
（未定义时 conflictWithGlobalShortcuts() 直接 return false），patch 0001 把
HAVE_KGLOBALACCEL 置 FALSE——OHOS 无桌面全局快捷键注册表，语义与上游对
ANDROID/IOS 的特判一致，不损失任何 QML 模块。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | KDEInstallDirs 的 ecm_query_qt 调 qtpaths 报 libc++_shared.so not found (exit 127) | 本机 shell LD_LIBRARY_PATH 有空格污染条目（"chipset-pub-sdk:&lt;空格×9&gt;/system/lib64"），OHOS loader 遇空格路径解析中止，qtpaths 连 /system/lib64 的 libc++_shared.so 都找不到 | 启动 conan create 前清洗：`export LD_LIBRARY_PATH=$(echo "$LD_LIBRARY_PATH" \| tr -s ' ' \| sed 's/: */:/g; s/^ *//; s/ *$//; s/:$//')`。清洗后 qtpaths 立即恢复。CI 远端 clean 环境无此污染（kirigami 6.18.0 同结构配方 CI 已绿为先证） |
| 2 | ECMQmlModule include 陷阱（knotifications PR #8662 同链预警） | ECMQmlModule6.cmake 内部无 QUIET 的 find_package(Qt6 COMPONENTS Core Qml CONFIG)——qtbase 裁剪包无 Qml 组件时会 FATAL | 本包无需 patch：qtdeclarative/6.11.1 在依赖里提供 Qt6Qml，find_package 直接成功。与 knotifications 场景的本质差异：knotifications 的 QML 是可选线（qtbase 无 Qml），本包 QML 是核心且 Qml 组件可得 |
| 3 | test_package 首版用 KIRIGAMIADDONSCOMPONENTS_VERSION 字符串断言编译失败 | ecm_setup_version 生成的 *_VERSION 宏是整数位掩码 ((1<<16)\|(13<<8)\|(0))，字符串版是 _VERSION_STRING | 改用 KIRIGAMIADDONSCOMPONENTS_VERSION_STRING == "1.13.0" + MAJOR/MINOR/PATCH 三段断言 |

## 测试说明（N 申报）

上游构建系统注册的 CTest add_test 数：**6**（autotests/CMakeLists.txt 的
kirigami_add_tests 宏注册 tst_avatar/onboarding/sounds/album_qmllistmodel/
album_abstractlistmodel/album_qmlqobjectmodel 6 项）。**全部已构建并在配方内
真跑**（BUILD_TESTING=ON + _test_env：QT_QPA_PLATFORM=offscreen +
QML2_IMPORT_PATH 三级注入 + LD_LIBRARY_PATH 双布局收集）：tst_avatar /
tst_onboarding 2 项绿（2/6 PASS）；其余 4 项在 QML 编译期报
"module QtMultimedia is not installed"（tst_sounds.qml:11 直接触发；
album×3 经 VideoMaximizeDelegate.qml:7 链式触发）——制品仓
qtmultimedia/6.11.1 只含 C++ 库无 qml/ 导入树（其配方 requires 无
qtdeclarative），QtMultimedia QML 绑定不在仓，逐项报错定位排除。
消费者侧补全：test_package 3 组断言（version header 字符串+三段、
NameUtils::initialsFromString/colorsFromString/isStringUnsuitableForInitials
真实 API 面）——CTEST 1/1 PASS。

## 验证结果

OHOS `conan create` verification (2026-09-07):
- 22 包依赖图全解析（全 Cache，无源码编译依赖）
- 主包构建+打包成功（含 OHOS ELF 签名、DT_NEEDED 归一化）
- 上游测试 2/2（可跑子集）PASS：tst_avatar 0.60s / tst_onboarding 1.42s
- test_package: 1/1 PASS（cmake.find_package KF6KirigamiAddons + 链接
  KirigamiAddonsComponents + 真实 API 断言）

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（kirigami 6.18.0 先例七点打法 + qtmultimedia/KF6 依赖扩展）|
| conandata.yml | 源码 URL + sha256（扁平结构，同 kirigami 先例）|
| patches/0001-CMakeLists-disable-kglobalaccel-for-ohos.patch | KGlobalAccel 禁用（HAVE_KGLOBALACCEL=FALSE 优雅降级）|
| test_package/ | NameUtils API 三断言 + version header 校验 |
---

**编译结束**: 2026-09-07 02:14
**最终状态**: built
