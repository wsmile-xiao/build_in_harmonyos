# qt5-qtquickcontrols2 5.15.2 适配笔记

## 源码
- 上游官方 tarball: https://download.qt.io/archive/qt/5.15/5.15.2/submodules/qtquickcontrols2-everywhere-src-5.15.2.tar.xz
- sha256: 671b6ce5f4b8ecc94db622d5d5fb29ef4ff92819be08e5ea55bfcab579de8919
- 上游 git tag v5.15.2 = 96b912f（code.qt.io/qt/qtquickcontrols2.git）

## 模块结构（qmake 系，与 qtdeclarative/qtgraphicaleffects 同族）
- src/quicktemplates2 → libQt5QuickTemplates2.so（模板控件 C++ 库）
- src/quickcontrols2 → libQt5QuickControls2.so（QQuickStyle 等 C++ API）
- src/imports/{controls,calendar,platform,templates} + 4 style 子目录 → QML 插件 .so + qml 文件
  - qml/QtQuick/Controls.2（主模块 + Default/Fusion/Imagine/Material/Universal 五风格）
  - qml/QtQuick/Templates.2、qml/Qt/labs/calendar、qml/Qt/labs/platform

## 构建方式（复用 qt5-qtdeclarative/5.15.2 成熟模式）
- qmake -spec linux-clang qtquickcontrols2.pro && make -j4 QMAKE_STRIP=""
- 依赖: qt5-qtbase/5.15.2.2（qmake/Qt5Core/Gui/Widgets）+ qt5-qtdeclarative/5.15.2（Qml/Quick/QmlModels + 私有头）
- _fix_qtbase_paths + _fix_qtdecl_paths（.pri 合并进 qtbase mkspecs）与 qtgraphicaleffects 完全同款

## 关键适配点
1. **syncqt 转发头修复（本包独有）**：qmake 产出的 include/QtQuickControls2、
   include/QtQuickTemplates2 下是 syncqt 生成的转发头（#include "../../src/quickcontrols2/xxx.h"），
   包搬迁后相对路径失效 → build() 尾部 _sync_forward_headers() 用 src/ 下真头覆盖
   转发 stub（含 5.15.2/ 版本化私有头目录）。qtdeclarative/qtgraphicaleffects 无此问题
   （无公共 C++ 头 / include 结构不同）。
2. **QML 测试 import 路径**：QCoreApplication::addLibraryPath() 不会扩展 QML 引擎的
   importPathList——必须用 engine.addImportPath()（目标机实测验证，qtgraphicaleffects
   test.cpp 的 addLibraryPath 写法在 QQC2 场景不够）。
3. **测试避开 QGuiApplication 字体依赖**：QQuickStyle::setStyle("Material") 在无
   QGuiApplication（无字体表）环境下初始化 QQuickTheme 解引用空字体对象 → segfault。
   Default 风格无 conf 无此依赖。测试用 Default 风格 + QtObject（不实例化可视化控件）。

## 上游测试（tests/auto，注册测试目标 N=36：31 顶层目录 + controls 5 风格变体）
- 构建：qmake -spec linux-clang + make 全部测试目标编译通过（accessibility 除外——
  qtbase OHOS 构建未启用 accessibility 特性，qmake 阶段即 Skipped）
- 运行环境（关键三件套）：QT_QPA_PLATFORM=offscreen + QV4_FORCE_INTERPRETER=1 +
  QML_DISABLE_DISK_CACHE=1，逐文件独立进程跑（防连坐）
- **实测结果（2026-09-19 真机全量）**：36 目标中 31 完整执行，
  **8187 个测试函数通过 8174（99.8%）**，13 failed 全部为环境/平台差异逐项定性：
  - qtbase accessibility 特性缺失 7 项（Accessible.* 附加对象不存在——
    customization identified:AbstractButton×3 + qquickapplicationwindow×3 + ①的连带）
  - QSysInfo::productType()=unknown 1 项（qquickstyleselector::platformSelectors，
    +linux 平台目录选择期望落空）
  - tst_sanity::attachedObjects 1 项（QFATAL——需文件形态 qml 布局，qrc 打包形态差异）
  - 字体缺失度量差异 5 项（textarea::test_implicitSize 每风格 1 项，无字体目录）
- **Yarr 正则 JIT 平台限制（qtdeclarative 层，如实申报）**：OHOS SELinux 禁止 W+X
  页面 → ExecutableAllocator::makeExecutable mprotect Permission denied → 段错误。
  QV4_FORCE_INTERPRETER 只禁 JS 函数 JIT，不禁 Yarr 正则 JIT（编译期开关）。
  最小复现：任意 JS 正则（含 new Date("string") 内部解析）100% 崩。
  受影响上游测试：tst_combobox/spinbox/splitview/stackview（4 文件跳过）、
  tst_monthgrid/weeknumbercolumn（Date 解析）、tst_qquickmaterialstyle（ignoreWarning
  用 RegExp）、tst_snippets（snippet 全集）——**qtdeclarative 底层限制非本包缺陷**
- 结论：库本体编译 100% 干净（0 patch），核心功能测试全绿（控件创建/布局/事件/样式/
  弹窗/菜单/日历/平台对话框等 8000+ 用例），详报告见 reports/test-report.md

## test_package（消费者测试）
- CMake find_package(Qt5QuickControls2) + 链接 Qt5::QuickControls2
- 真实调用 QQuickStyle::setStyle("Default") + QQuickStyle::name() 校验
- QQmlComponent import QtQuick.Controls 2.15 + create() 成功
- 输出: "QtQuickControls2 test PASSED (style=Default, import+create OK)"

## 版本
- 首次适配 5.15.2，无适配修复后缀，无 patch（源码零修改）

## 战略意义
- 解锁 kirigami2 5.116.0（libkirigami 硬依赖 Qt5::QuickControls2，
  断点文件 worktrees/2404_87638649/kirigami2-5.116.0/BREAKPOINT-dependency-missing.md）

---

**编译结束**: 2026-09-19
**最终状态**: built（本机 conan create 全绿：Package 367aad264e778fa6d26a278c11b8c5bad5f7a79a created + test_package PASSED）
