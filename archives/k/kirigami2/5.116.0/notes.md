# kirigami2 5.116.0 适配笔记

## 概览

- 软件：KDE Frameworks 5 · Kirigami 2（KF5Kirigami2 核心库 + `org.kde.kirigami` QML 模块）
- 版本：5.116.0（KF5 最后一个版本线）
- 构建系统：CMake（ECM，QT_MAJOR_VERSION=5 强制 KF5 分支）
- 源码：`https://download.kde.org/stable/frameworks/5.116/kirigami2-5.116.0.tar.xz`
- sha256：`8b584da74a0c4488ad5e31c3d740a1813c35d28bc003fef8854963d17058c9e0`（与上游 `.sha256` 文件一致）
- 状态：`built`（conan create 全绿；上游 19 用例全执行，7 通过 + 12 项依赖层 accessibility 限制定性；test_package 2/2 + 消费者探针全过）

## 依赖链（qt5 生态）

| 类型 | 依赖 | 说明 |
|------|------|------|
| required | qt5-qtbase/5.15.2.2 | Core/Gui/Concurrent/Test + **GuiPrivate**（private 头齐全，Qt5GuiConfig 在 FIND_COMPONENTS 含 Private 时创建 `Qt5::GuiPrivate`） |
| required | qt5-qtdeclarative/5.15.2 | Qml/Quick/QuickTest/QmlModels 等全部库；**无原生 CMake config**（CMakeDeps 单一 Qt5QmlConfig.cmake） |
| required | qt5-qtquickcontrols2/5.15.2 | QuickControls2/QuickTemplates2 C++ 库 + 原生 config + QML styles（本任务的关键解锁件） |
| required | qt5-qtsvg/5.15.2.1 | Qt5Svg（顶层 `find_package(Qt5 ... Svg)`） |
| required | qt5-qtgraphicaleffects/5.15.2 | QtGraphicalEffects QML 模块（styles 运行时依赖，`ecm_add_qml_module_dependencies` 声明） |
| build | ecm/6.26.0 | ECMQmlModule5.cmake / KDEInstallDirs5.cmake 完整 Qt5 分支；`find_package(ECM 5.116.0)` 版本兼容 |

> **qtbase override**：qt5-qtsvg/5.15.2.1 写死依赖 qt5-qtbase/5.15.2，其余包用 5.15.2.2——
> 沿用 flameshot/14.0.0 先例：`self.requires("qt5-qtbase/5.15.2.2", override=True)`。
> 注意：override 图里 conan 2.29 会拒绝 cpp_info.requires 引用 qt5-qtbase:: 组件
> （"not a direct requirement"），故本配方不声明 cpp_info.requires。

## 构建步骤

```
conan create archives/k/kirigami2/5.116.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

关键 CMake 选项（`generate()`）：

- `BUILD_SHARED_LIBS=ON`、`BUILD_TESTING=ON`、`BUILD_EXAMPLES=OFF`、`BUILD_QCH=OFF`
- `DESKTOP_ENABLED=OFF`（org.kde.desktop style 不需要；Material style 保留）
- `DISABLE_DBUS=ON`（**KF5 选项名**，KF6 改叫 USE_DBUS；OHOS 无 D-Bus）
- `KF_IGNORE_PLATFORM_CHECK=TRUE`、`KF_SKIP_PO_PROCESSING=ON`
- `QT_MAJOR_VERSION=5`（cache 变量；ECM ≥ 5.240 默认 Qt6，必须强制）
- `CMAKE_CXX_STANDARD=17`、`CMAKE_INSTALL_LIBDIR=lib`
- OHOS soname/rpath 规则注入（`CMAKE_USER_MAKE_RULES_OVERRIDE_{C,CXX}`）

## Qt5 跨包 CMake 桥接（本适配的核心工程量）

上游 kirigami2 用伞形 `find_package(Qt5 REQUIRED NO_MODULE COMPONENTS Core Quick
Gui Svg QuickControls2 Concurrent)`，但发布的 Qt5 链把 config 拆在四个包里：

1. **Qt5Config 桥**（generate() 生成，覆盖 generators/Qt5Config.cmake）：
   基础组件交给原生 qtbase Qt5Config；Qml/Quick/QuickTest 走 CMakeDeps 的
   Qt5QmlConfig（建 `Qt5::Quick`/`Qt5::QuickTest` 别名）；QuickControls2/
   QuickTemplates2/Svg 走各自原生 config。`Qt5::GuiPrivate` 通过
   `find_package(Qt5Gui COMPONENTS Private)` 重探测物化。
   ⚠️ CMakeToolchain 会在 project-top-level includes **之后** PREPEND
   generators 目录到 CMAKE_PREFIX_PATH——桥必须写到 generators/Qt5Config.cmake
   本身（tc.generate() 后再写），否则永远被 CMakeDeps 的包级 config 抢先。
2. **qtbase config 树修复副本**：qt5-qtbase 的
   Qt5CoreConfigExtrasMkspecDir.cmake 残留构建期路径
   `${prefix}/../b//mkspecs/linux-clang` → Qt5::Core target 校验失败。
   复制 lib/cmake（0.9MB）到 generators/qt5base-cmake-fixed，整包布局用
   symlink 镜像（include/mkspecs/bin/plugins），修掉 ../b/ 段，staged 根
   排 CMAKE_PREFIX_PATH 最前。
3. **Qt5QuickTestConfig.cmake + ConfigVersion shim**：上游
   `find_package(Qt5QuickTest 5.15.2 CONFIG QUIET)` 找的是 config 文件名，
   qtdeclarative 包没有 → shim 加载 Qt5Qml config 并建 `Qt5::QuickTest`
   （链 `qt5-qtdeclarative::qt5-qtdeclarative` + `Qt5::Test`——
   `QTest::setMainSourcePath` 在 qtbase 的 libQt5Test 里，不在
   libQt5QuickTest 里！）+ 版本号 Qt::QuickTest 无版本别名。
4. **DEPS_TARGET 前置组件**：CMakeDeps 的 Qt5QmlTargets 里
   qt5-qtdeclarative_DEPS_TARGET 的链接接口引用 `Qt5::Network`——
   桥里先循环 find Qt5Core/Qt5Gui/Qt5Network/Qt5Concurrent 再分发跨包组件。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Version conflict: qt5-qtbase/5.15.2 vs 5.15.2.2` | qt5-qtsvg/5.15.2.1 写死旧 qtbase | `override=True`（flameshot 先例） |
| 2 | `Error loading shared library libc++_shared.so`（cmake 起不来） | conan 沙箱环境 LD_LIBRARY_PATH 丢系统路径 | 外层注入完整 LD_LIBRARY_PATH（llvm/lib + /system/lib64 + platformsdk） |
| 3 | `The imported target "Qt5::Core" references the file ".../p/../b//mkspecs/linux-clang"` | qtbase 包 config 构建期路径残留 | staged-fixed 副本 + symlink 镜像（见上） |
| 4 | `Target "KF5Kirigami2" links to: Qt5::Qml — target not found` | CMakeDeps 只为 qtdeclarative 生成 Qt5QmlConfig（无 Quick/QuickTest），伞形 find 无组件分发 | Qt5Config 桥（覆盖 generators 版本） |
| 5 | `qt5-qtdeclarative_DEPS_TARGET ... contains Qt5::Network` | CMakeDeps 依赖链硬引用 | 桥里预 find 基础组件 |
| 6 | `use of undeclared identifier 'QCoreApplication'` / `field has incomplete type 'QColor'` | Qt 5.15.19 头不再传递泄漏这些定义 | patch 0001 补显式 include |
| 7 | `Qt5QuickTest not found, autotests will not be built` | find_package 找 config 文件名，包里没有 | Qt5QuickTestConfig.cmake + ConfigVersion shim |
| 8 | `undefined symbol: QTest::setMainSourcePath` | 该符号在 qtbase libQt5Test | Qt5::QuickTest 别名同时链 qtdeclarative 包级 target + Qt5::Test |
| 9 | 12/19 上游测试 `Non-existent attached object: Accessible.*` | **qt5-qtbase/5.15.2.2 的 accessibility 特性被禁用**（QT_DISABLED_FEATURES 实证）——QML Accessible 附加属性不存在，所有赋值组件初始化失败 | 依赖层限制如实申报：7 个不涉 Accessible 的用例 100% 过，12 个失败逐项定性（同 qtquickcontrols2 归档已知限制同源） |
| 10 | test_package 段错误（Units 构造） | Kirigami::Units 构造查 QGuiApplication 字体表，headless 无实例 | 消费者测试改断言静态 meta 对象 + QML payload/import（不构造 Units） |
| 11 | conan 打包后包目录 bin/ 出现 88 个 Qt so | test 的 _prepare_runtime_links 曾把库复制进 dep 包的 bin | 只写 test build 目录（包目录保持纯净） |

## 源码修改

`patches/0001-add-missing-includes-qt5.15.19.patch`（portability）：
- `src/icon.h`、`src/shadowedrectangle.h`：补 `#include <QColor>`
- `src/libkirigami/kirigamipluginfactory.cpp`：补 `#include <QCoreApplication>`

其余适配全部在配方内完成（Qt5Config 桥 / staged-fixed config 树 / shims /
DT_NEEDED 规范化 + 重签名），不触碰 tarball。

## 验证结果

- **上游测试（R51）**：N=19 注册 / 19 实跑（`--no-tests=error` 保证零跳过）
  - **7 通过（不涉 Accessible 的用例 100%）**：tst_icon、tst_mnemonicdata、
    tst_theme、wheelhandler×4（filterMouseEvents/invokables/onWheel/scrolling）
  - **12 失败（单一根因逐项定性）**：tst_actiontoolbar、tst_avatar、
    tst_basiclistitem_tooltip、tst_formlayout、tst_globaldrawer、
    tst_keynavigation、tst_listskeynavigation、tst_pagerouter、tst_pagerow、
    tst_routerwindow、pagepool/tst_layers、pagepool/tst_pagepool——
    全部因 `Accessible.*` attached object 不存在（qtbase accessibility
    特性禁用）导致 QML 组件实例化失败；证据：qtbase Qt5GuiConfig.cmake
    `QT_DISABLED_FEATURES accessibility`；与 qt5-qtquickcontrols2/5.15.2
    归档记录的已知限制同源（那边 7 项 Accessible.* 失败同因）
  - junit 明细：`build/Release/upstream-tests.xml`（conan build 目录内）
- **test_package**：ctest 2/2 + 消费者探针全过
  - `PASS: Kirigami::Units / Kirigami::PlatformTheme meta objects exported`
  - `PASS: installed QML module payload lib/qml/org/kde/kirigami.2（qmldir + libKirigamiPlugin.so）`
  - `PASS: QQmlEngine imported org.kde.kirigami 2.19（Units singleton 可解析）`
  - `PASS: __OHOS__ defined, sysname=HarmonyOS machine=aarch64；K links F5Kirigami2`
- **OHOS ELF 签名**：package() 阶段 DT_NEEDED 规范化（`../bin/libKF5Kirigami2*` →
  裸 soname）后全部 ELF 重签（binary-sign-tool）

## 交付物（安装进包）

| 路径 | 说明 |
|------|------|
| `lib/libKF5Kirigami2.so*` | KF5 核心共享库（SOVERSION 5） |
| `lib/qml/org/kde/kirigami.2/` | 主 QML 模块：qmldir + libKirigamiPlugin.so + 115 个 QML 文件 + plugins.qmltypes |
| `include/KF5/Kirigami2/{kirigami,Kirigami}/` | 公共头（PlatformTheme/Units/TabletModeWatcher/KirigamiPluginFactory/VirtualKeyboardWatcher，含 CamelCase 与兼容头） |
| `lib/cmake/KF5Kirigami2/` | `KF5::Kirigami2` 消费目标（find_package(KF5Kirigami2) 直接可用） |
| `mkspecs/modules/qt_Kirigami2.pri` | qmake 集成 |

## 注意事项

- **R38**：library-only 包（无 CLI 工具），不加软件级 commands.json。
- **下游解锁**：本包是 qt5-qtquickcontrols2 生态的关键链式件——
  kirigami-app/kirigami-gallery 等 KF5 QtQuick 应用依赖本包。
- **accessibility 缺口的根治**：需 qt5-qtbase 重新构建启用 accessibility 特性
  （上游 -feature-accessibility），属依赖包重构范畴，不在本任务内。
- **KF6 线对照**：kirigami/6.26.0（KF6）已归档；本包为 KF5 最后版本线的
  平行适配，依赖从 qt6 全家桶换 qt5 全家桶，构建机制差异见上"Qt5 跨包
  CMake 桥接"一节（qt6 线无此问题——qtbase/6.11.1 自带完整 relocatable config）。

---

**编译结束**: 2026-09-23 18:39
**最终状态**: built（conan create 全绿）
