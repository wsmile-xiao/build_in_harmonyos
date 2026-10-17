# kxmlgui 6.26.0 适配笔记

## 编译环境
- 构建系统: cmake (ECM)
- 编译日期: 2026-09-19
- 编译器: clang/clang++ 15 (OHOS SDK, aarch64-linux-ohos)
- 状态: built
- worktree: ~/huawei/worktrees/j669539/kxmlgui-6.26.0

## 软件简介

kxmlgui 是 KDE Frameworks 6 的 XML GUI 框架库（libKF6XmlGui.so）：为
KMainWindow/KXmlGuiWindow 提供基于 XML 的菜单/工具栏描述、动作集合
（KActionCollection）、快捷键编辑器（KShortcutsEditor）等，是 kcmutils
（任务 #13728）与 kinfocenter（任务 #12847）依赖链上的解锁件。

本件是 KF6 6.26 线升级（前版 6.14.0/6.18.0 已在 main），基于 6.18.0
配方骨架 + 6.26.0 源码，与 6.26 链其它件（kitemviews PR #8491、
kiconthemes PR #8674 同作者先例）同一打法。

## 与 6.18.0 配方的差异

| # | 变更 | 原因 |
|---|------|------|
| 1 | 依赖矩阵 6.18 → 6.26（kconfig/kcoreaddons/kguiaddons/ki18n/kiconthemes/kitemviews/kwidgetsaddons） | ohpcd 已发布 6.26 线（W0 逐个 conan download 核验） |
| 2 | kconfigwidgets 保持 6.18.0 + `override=True` 顶传递依赖到 6.26 | **kconfigwidgets/6.26.0 未发布且无任务**（全量任务池+PR 扫描确认）；kconfigwidgets/6.18.0 的 recipe 锁 6.18 线传递依赖，与 6.26 线同图会触发 conan Version conflict（实测 `Conflict between ki18n/6.26.0 and ki18n/6.18.0`）——override 后整图唯一 6.26 版本 |
| 3 | 补丁 0001 重生成：PrintSupport 下线 + `find_package(KF6ConfigWidgets 6.18.0 REQUIRED)`（原为 `${KF_DEP_VERSION}`=6.26.0） | 6.26 源码 REQUIRED_QT_VERSION 6.7.0→6.9.0 行号偏移，6.18 补丁 FAILED 43/43；同时 KF6ConfigWidgets 版本地板降为已发布的 6.18.0 cap |
| 4 | 补丁 0002 重生成（去 `Qt6::PrintSupport` 私链，6.26 行号偏移） | 同上 |
| 5 | 补丁 0003 重生成（printShortcuts 全掏空 + KShortcutsDialog Print 按钮移除） | 6.26 源码结构未变，行号偏移 |
| 6 | 补丁 0004 重生成（QLocale 语言行运行时 skip） | 6.26 行号 1220→1222 |
| 7 | LD_LIBRARY_PATH 前置 /system/lib64 | 沙箱 libc++_shared.so 遮蔽（kconfig 6.26.0 先例） |

### KF6::IconWidgets 来源（6.26 新增依赖）

6.26 的 kxmlgui src/CMakeLists.txt 新增 `KF6::IconWidgets`（KIconDialog）。
该目标由 kiconthemes/6.26.0 提供（上游 src/widgets 拆分出
libKF6IconWidgets.so，KF6IconThemesTargets.cmake 同时定义
KF6::IconThemes 和 KF6::IconWidgets 两个 imported target）——已实测制品仓
包内含 libKF6IconWidgets.so.6.26.0 + include/KF6/KIconWidgets，无需额外
find_package，也无需新增依赖包。

## conan override 方案验证记录

- 实测 A（无 override）：`conan install --requires=kconfigwidgets/6.18.0
  --requires=kiconthemes/6.26.0` → `ERROR: Version conflict: Conflict
  between ki18n/6.26.0 and ki18n/6.18.0 in the graph. Conflict originates
  from kiconthemes/6.26.0`
- 实测 B（override）：同图 + `self.requires("ki18n/6.26.0", override=True)`
  等 7 项 override → graph 解析成功，全图唯一 6.26 版本，无冲突
- 注意：override 会改变 kconfigwidgets/6.18.0 的 package_id（其原二进制
  package_id 基于无 override 的图）。W3 `conan create --build=missing` 时
  conan 会从源码重建 kconfigwidgets/6.18.0（耗时约几分钟，可接受——
  该包无 override 版本 recipe 已在缓存，源码重建走同一配方）。

## 编译步骤

conan create（模式 A）：
```
conan create archives/k/kxmlgui/6.26.0 \
  -pr:h ~/.conan2/profiles/ohos-aarch64 -pr:b ~/.conan2/profiles/ohos-aarch64 \
  --build=missing
```
关键 CMake 配置：
- `-DBUILD_SHARED_LIBS=ON -DBUILD_TESTING=ON`
- `-DKF_IGNORE_PLATFORM_CHECK=TRUE`（OHOS 不在 KDE 平台列表）
- `-DFORCE_DISABLE_KGLOBALACCEL=ON`（KF6GlobalAccel 未发布）
- `-DUSE_DBUS=OFF`（qtbase 基线无 Qt6DBus）
- `-DBUILD_DESIGNERPLUGIN=OFF`（Qt6UiPlugin 未发布）
- `-DBUILD_PYTHON_BINDINGS=OFF`（无 Shiboken6/PySide6）
- `-DKF_SKIP_PO_PROCESSING=ON`（无 Qt6LinguistTools）
- ECM_MODULE_PATH 手工注入（CMakeDeps 生成的 ECMConfig 不传播该变量）
- conan_cmakedeps_paths.cmake 手工生成（qtbase cmake_find_mode=none）

## 上游测试（N=82 审核员实测口径，rule4 少报修正 2026-09-19）

上游测试体系三层构成（BUILD_TESTING=ON 下 autotests + tests 全集）：

1. **autotests/**（ecm_add_tests 注册 6 个 CTest 目标，62 个 QTest 函数）：
   kactioncategorytest(3) kactioncollectiontest(14) kmainwindow_unittest(10)
   ktoolbar_unittest(8) ktooltiphelper_unittest(4) kxmlgui_unittest(23)。
   6 个参数化函数展开 36 数据行（ktoolbar 16 + kxmlgui 20）。
2. **tests/**（8 个手动 GUI 验证程序，ecm_mark_as_test，无 QTest 断言）：
   kbugreporttest kmainwindowrestoretest kmainwindowtest krulertest
   ktoolbartest kwindowtest kxmlguitest kxmlguiwindowtest。
3. **tests/krichtexteditor**（1 个，KTextWidgets 条件构建）。

本机（arm64 OHOS）实测（QT_QPA_PLATFORM=offscreen，干净 test-home）：
- autotests 逐 exe Totals：5+16+12+22+6+43 = **104 执行断言组全部通过，
  0 failed 0 skipped**（含 init/cleanupTestCase；conan create 内 ctest
  6/6 目标 Passed 双通道复验一致）。
- tests/ 8 个 GUI 程序启动运行验证 rc=0 无崩溃（offscreen 事件循环等待
  属 GUI demo 正常行为）。
- krichtexteditor 豁免：KTextWidgets 未发布到 ohpcd（conan download
  验证配方不存在），上游 find_package(KF6TextWidgets QUIET) 查找失败
  不构建该子目录。
- 注意：复验时 test-home 必须干净——kxmlgui_unittest 的
  testHiddenToolBar/testAutoSaveSettings 依赖 KConfig 状态，污染的
  test-home 会产生假失败（实测：干净 43/43 过 vs 污染 41+2 败）。
  conan create 配方的每次全新 test-home 设计正是为此。

## 依赖核验（W0，R35 conan download 口径）

qtbase/6.11.1 ✅ kconfig/6.26.0 ✅ kcoreaddons/6.26.0 ✅
kguiaddons/6.26.0 ✅ ki18n/6.26.0 ✅ kiconthemes/6.26.0 ✅
kitemviews/6.26.0 ✅ kwidgetsaddons/6.26.0 ✅ openssl/3.5.6.1 ✅
zstd/1.5.7 ✅ ecm/6.26.0 ✅ kconfigwidgets/6.18.0 ✅（cap）
kcolorscheme/6.26.0 ✅ kcodecs/6.26.0 ✅（override 目标）
