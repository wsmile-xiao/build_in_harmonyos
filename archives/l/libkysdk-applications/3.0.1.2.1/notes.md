# libkysdk-applications 3.0.1.2.1 — HarmonyOS PC 适配笔记（Qt6 构建）

> 协作者模式 · SKILL `openharmony-compile-agent` · 2026-10-10
> **状态：`built`**（conan create exit 0 + conan-verify G1–G4/L2/L4/L5 通过；W3 本地 CI 绿）
> 本版本是 REDO：修复独立审计（W4）在 P0/R40（stub + 错误理由）与 P1/R33 上发现的缺陷。

### 对话 #1（2026-10-10，redo）

* 输入：独立审计判定当前 PR `#15238`（head `d09dee1a…`）存在 P0/R40 + P1/R33。
* 动作：把 Qt5 期补丁里**误删但 Qt6 实际可用**的能力恢复（可访问性名称/描述、Qt6Svg、
  Qt6Sql、`QPalette::Accent`、QGSettings），删除所有 “OHOS 无 Qt5 …” 的错误注释；
  修正 `test_package` 的编译器选择；整体重新生成补丁集并重跑 W3。
* 结果：`.ci-result.json exit_code=0`（真实重建），`conan-verify` 全绿，见 §4/§5。

## 0. 为什么需要这个版本

下游 `kylin-nm-plugin/4.0.0.1` 是 **Qt6/qmake** 的 openKylin/UKUI 网络小程序：

* `.pro` 里 `PKGCONFIG += kysdk-applications`；
* 6 个源文件 `using namespace kdk;`，真实使用 `KSwitchButton` / `KBorderlessButton` /
  `KTabBar(KTabBarStyle::SegmentDark, …)` / `KPasswordEdit` / `class LogHintDialog : public KDialog`。

这些类都派生自 Qt 控件类，因此**用 Qt5 编译的 kysdk 与 Qt6 消费者 ABI 不兼容**。
制品仓里只有 `libkysdk-applications/3.0.1.2`（Qt5，依赖 `qt5-qtbase/5.15.2.2`）。
本版本（R37 适配后缀 `.1`）在原版 3.0.1.2 源码上做**纯 Qt6 重定向**。

## 1. 版本与源码

| 项 | 值 |
|----|----|
| 版本 | `libkysdk-applications/3.0.1.2.1`（上游 3.0.1.2 + 适配后缀 `.1`，R37） |
| 源码 URL | `https://deb.debian.org/debian/pool/main/libk/libkysdk-applications/libkysdk-applications_3.0.1.2.orig.tar.xz` |
| sha256 | `57ea0648ed4f6e3f7d29db75ff3363e7ff958e48b4047bda5e5aa4d519ab1777` |
| 上游仓库 | `https://gitee.com/openkylin/libkysdk-applications` |
| 上游版本 | 3.0.1.2 |

## 2. W0 依赖门禁（R35：只用 `conan download`）

```
$ conan download "qtbase-sql-dbus/6.11.1" -r=ohpcd --only-recipe   -> rev 651deb09…
$ conan download "qtsvg/6.11.1"           -r=ohpcd --only-recipe   -> rev 49bc7f51…
$ conan download "gsettings-qt/1.1.1"     -r=ohpcd --only-recipe   -> rev e3c96744…
$ conan install --requires=gsettings-qt/1.1.1 -pr:h=ohos-aarch64 … -> Already installed (binary 已发布)
```

结论：三个直接依赖（`qtbase-sql-dbus/6.11.1`、`qtsvg/6.11.1`、`gsettings-qt/1.1.1`）**均已发布**，
本地缓存已含 `os=OHOS/armv8/clang15/libc++/cppstd17` 二进制，W0 门禁通过。

## 3. lang-preflight（R47）

* 期望语言（任务默认）：`cpp`；检测：构建系统 = qmake（C++），源码主体 = 90+ 个 `.cpp`/`.h`。
* 结果：**匹配（cpp）**。

## 4. 构建系统与依赖（实测 `.pro` 为准）

顶层 `kysdk-application.pro`（TEMPLATE=subdirs）在补丁后只构建 4 个模块：
`kysdk-widgetutils` / `kysdk-qtwidgets`（下游需要的 kdk:: 控件集）/ `kysdk-alm` / `kysdk-ukenv`。

| 需求 | 来源 | 说明 |
|------|------|------|
| qmake6 + Qt6Core/Gui/Widgets/**DBus**/Network/**Sql** | `qtbase-sql-dbus/6.11.1` | `FEATURE_dbus=ON` + `FEATURE_sql=ON`（`QT += dbus sql`） |
| Qt6Svg（`QSvgRenderer`） | `qtsvg/6.11.1` | `kalendar` 日期控件 SVG 图标渲染（**已恢复**） |
| QGSettings（`gsettings-qt6`） | `gsettings-qt/1.1.1` | 主题控制器 / ukenv 设置监视 / widgetutils 合成器探测（**已恢复**） |
| KF6WindowSystem / X11 / xcb / wayland / KWindowEffects / UKUI 装饰 | **不需要** | 0001–0003 补丁裁剪（OHOS 上确实不可得，保留裁剪） |

实测 `libkysdk-qtwidgets.so` 链接行：`-lgsettings-qt6 -lQt6Svg libQt6Widgets/Gui/Sql/DBus/Core`。

**为什么 Qt6Svg / QGSettings 用环境变量注入前缀，而不是 `QT += svg` / `PKGCONFIG += …`：**

* Qt6Svg 是**独立的 Conan 包**，其 qmake 模块 `.pri`（`$$QT_MODULE_INCLUDE_BASE`）会把 include
  解析到 **qtbase 前缀**（`-I<qtbase>/include/QtSvg`），指向错误目录 → 不能用 `QT += svg`。
* qtsvg 与 qtbase-sql-dbus 都不提供可用的 pkg-config（Qt6 模块 `.pc` 缺失或带**陈旧绝对 prefix**，
  见 §8-5）。
* 因此 `conanfile.build()` 通过 `Environment` 注入 `KYSDK_QTSVG_INCLUDE/LIBDIR`、
  `KYSDK_GSETTINGS_INCLUDE/LIBDIR`，由各 `.pro` 转成 `INCLUDEPATH`/`LIBS`。
* Qt6Svg 会传递拉入 `qtbase/6.11.1`（纯版）；它与 `qtbase-sql-dbus/6.11.1` 在同一图中共存——
  与兄弟配方 `kirigami/6.18.0`、`kshisen/26.04.0` 的既有做法一致（二者同样同时依赖
  `qtbase-sql-dbus` + `qtsvg`）。运行时同名 `libQt6Core.so.6` 只加载一份。

## 5. 补丁集（72 个，`ohc-run.py refresh-patch --auto` 产出）

补丁集 = **原始 3.0.1.2 tarball → 最终适配树**的逐文件 diff（`orig_dir=pristine`、
`work_dir=final`）。**补丁文件本身不含任何平台宏或注释**（`refresh-patch` 只产 raw diff）。

### 5.1 保留的“确实不可得”裁剪（OHOS 无对应依赖链）

* `kysdk-application.pro`：裁 `kysdk-appconf2` / `kysdk-waylandhelper` / `kysdk-kabase` 三个模块；
* `kysdk-qtwidgets`：裁 `-lX11` / `KF6WindowSystem x11` / `gsettings-qt6` / waylandhelper；
  `xatom-helper.{cpp,h}` 降为**保留 API 的空操作**（OHOS 无 X server）；去 `KWindowEffects` /
  `UKUI decoration` / `UkuiWindowHelper` 的窗口特效调用（保留绘制路径）；
* `kysdk-alm`：去 `PKGCONFIG += KF6WindowSystem`，`KX11Extras::forceActiveWindow` → `QWidget::activateWindow`；
* `tests/`：目标依赖裁剪（见 §7，本版本未构建上游测试）。

### 5.2 恢复的 Qt6 能力（REDO 的核心修复）

原补丁曾在**错误的 “OHOS 无 Qt5 模块” 理由**下删掉以下能力；由于本构建是 **Qt6.11**，
这些能力全部存在，予以**恢复**：

| 能力 | 位置 | 证据 |
|------|------|------|
| `QWidget::setAccessibleName/setAccessibleDescription` | `accessinfohelper.h`（`setAllAttribute`） | Qt6 核心 API，恢复为原始实现 |
| `KCustomTabBar` 可访问性（`#ifndef QT_NO_ACCESSIBILITY`） | `kcustomtabbar.cpp`（Tab::accessibleName / `setAccessibleTabName` + `QAccessible::updateAccessibility`） | Qt6 核心 API |
| Qt6Svg 图标渲染（`QSvgRenderer`） | `kcustomdateedit.cpp` / `klunardateedit.cpp` | `qtsvg/6.11.1` 已发布，恢复 `renderer.render(&painter)` |
| Qt6Sql `uksc.db` 应用名查询 | `kuninstalldialog.cpp`（`getAppCnName`） | `qtbase-sql-dbus` `FEATURE_sql=ON`，恢复 `QSqlDatabase/QSqlQuery` |
| `QPalette::Accent` | `themeController.cpp` | Qt6.2+ 核心枚举，恢复 `colorRole = QPalette::Accent` |
| QGSettings（真实类） | `themeController.cpp` 等 49 个私有 `.cpp`、`kysdk-ukenv/gsettingmonitor.{h,cpp}`、`kysdk-widgetutils/kwidgetutils.cpp` | `gsettings-qt/1.1.1`（Qt6 绑定）已发布；`#include <QGSettings>` 解析到 gsettings-qt 的头 |

**公共头不暴露 QGSettings**（保留的、有意为之的 API 洁净设计）：
`kswitchbutton.h` 不使用它（删除 include）；`themeController.h` 用前向声明 `class QGSettings;`。
仅需指针成员，因此消费者编译 `<kwidget.h>` 时**无需** gsettings-qt。

### 5.3 补丁可复现性验证

```
$ cp -r <pristine 3.0.1.2> verify && cd verify
$ for f in $(ls patches/*.patch | sort); do patch -p1 -i "$f"; done   # 全部 rc=0
$ diff -rq verify <final tree>   ->   0 differences（逐字节一致）
```

## 6. conanfile 设计要点

* `requirements()`：`qtbase-sql-dbus/6.11.1` + `qtsvg/6.11.1` + `gsettings-qt/1.1.1`（无 Qt5）。
* `settings.os in ("Linux","OHOS")`（R32）。
* `build()`：只用 `qmake6`（绝对路径）+ `make -jN`，**影子构建**；编译器/路径全部由
  `Environment` 显式注入（R33，不读裸 shell 变量），并注入 Qt6Svg / gsettings-qt 前缀（见 §4）。
  **不执行 `make install`**（上游 `target.path = $$[QT_INSTALL_LIBS]` 会写缓存/`/usr`）——
  `package()` 从构建树 staging，完全可重定位。
* `package_info().requires`：`qtbase-sql-dbus::{core,gui,widgets,network}` + `qtsvg::svg` +
  `gsettings-qt::gsettings-qt`（Conan 2 要求每个直接依赖都出现在 `cpp_info.requires`）。

## 7. 上游测试：清点与实测（R51，如实申报）

`tests/` 共 **7 个 QTest 目标 / 122 个 private-slot 方法**（逐文件清点）：

| 目标 | slots | Qt6 可构建 | 实测结果 |
|------|-------|-----------|---------|
| test-alm | 3 | ✅ | 构建成功并运行：5 passed / 0 failed，rc=0 |
| test-qtwidget | 76 | ✅ | offscreen 运行 2 passed 后 GUI 模态框阻塞（rc=124，90s 上限） |
| test-widgetutils | 1 | ❌ | qmake `CONFIG += testcase` → `qt_functions.prf:254`，`QMAKE_HOST.os=HarmonyOS` 不识别 → `Project ERROR: Operating system not supported.` |
| test-ukenv | 3 | ❌ | 同上（mkspec 缺口）——QGSettings 已恢复，仍受同一缺口阻塞 |
| test-appconf2 / test-kabase / test-wayland | 1/15/23 | ❌ | 对应模块被裁（依赖不可得） |

**本版本的 L1 测试**（`test_package/`）：真实消费者程序 `probe.cpp` —— 对**已安装**包执行
`pkg-config --cflags/--libs kysdk-applications` 并断言 `-I`，用这些 flags 编译并运行：
`dlopen(RTLD_NOW)` 4 个 `.so`（同时证明 Qt6Svg / gsettings-qt6 的 `DT_NEEDED` 可解析）、真实构造
`KSwitchButton`/`KBorderlessButton`/`KTabBar(SegmentDark)`/`KPasswordEdit`/`KDialog`/`KWidget`，
并**新增**：`setAccessibleName/Description` 往返断言 + `QPalette::Accent` 存在断言 +
`test()` 中核对 `libQt6Svg.so` / `libgsettings-qt6.so` 在依赖 libdir 中可见。

## 8. 关键排错记录

1. **公开头的 QGSettings 暴露**：`kwidget.h → … → themeController.h`。本版本设计为公共头不暴露
   QGSettings（前向声明），私有 `.cpp` 各自 `#include <QGSettings>`。
2. **`Qt6Svg` 的 qmake 模块前缀陷阱**：`QT += svg` 会把 include 指到 qtbase 前缀 → 必须显式注入
   前缀（§4）。
3. **`conan create` 的 package_info 校验**：直接依赖必须出现在 `cpp_info.requires`
   （`gsettings-qt::gsettings-qt`），否则 `ERROR: … not used by any '(cpp_info/components).requires'`。
4. **`gsettings-qt` 的 SONAME 不是 `.so.6`**：实际为 `libgsettings-qt6.so.1`——test_package 断言按
   前缀匹配（`libgsettings-qt6.so`）。
5. **已发布 `qtbase-sql-dbus` 的 Qt6 `.pc` prefix 陈旧**、glib 的 `gio-2.0.pc` prefix=`/`——
   因此 Qt6 模块 flags 一律从 `package_folder` 取，不用那些 `.pc`。

## 9. 未做 / 下一步

* 未 `conan upload`（属 release 流水线）。
* 三个被裁模块（appconf2/kabase/waylandhelper）要补回需先适配 kysdk-config、wayland-client、
  KF6WindowSystem 等依赖，超出“解开下游阻塞”的范围。

## 发现与知识（knowledge findings）

- ✅ Qt6 `QWidget::enterEvent` 取 `QEnterEvent*`（Qt5 取 `QEvent*`），Qt5 写法报 `non-virtual member function marked 'override' hides virtual member function`（[knowledge_ref: notes.md#findings-1]）
- ✅ Qt6 `QLabel::pixmap()` **按值**返回 `QPixmap`（Qt5 返回 `const QPixmap*`），判空/取值写法必须改写（[knowledge_ref: notes.md#findings-2]）
- ✅ **不得把 Qt5 期的“裁剪”带进 Qt6 构建**：`setAccessibleName/Description`、`QPalette::Accent`、Qt6Svg、Qt6Sql、QGSettings 在 OHOS Qt6 栈上都存在，必须恢复而非 stub；只有依赖**确实不可得**时才 stub，且必须写真实原因（[knowledge_ref: notes.md#findings-3]）
- ✅ Qt6Svg 是**独立 Conan 包**：`QT += svg` 的模块 `.pri` 会把 include 解析到 qtbase 前缀 → 必须显式注入 qtsvg 前缀（[knowledge_ref: notes.md#findings-4]）
- ✅ `qtsvg/6.11.1`（→ 纯 `qtbase/6.11.1`）与 `qtbase-sql-dbus/6.11.1` 可在同一图共存（`kirigami` / `kshisen` 先例）；`conanfile` 的每个直接依赖都必须出现在 `cpp_info.requires`（[knowledge_ref: notes.md#findings-5]）
- ✅ `gsettings-qt/1.1.1`（Qt6）头文件位于 `<prefix>/include/<arch>/qt6/QGSettings`，消费者写 `#include <QGSettings>`；公共头保持不暴露（前向声明）（[knowledge_ref: notes.md#findings-6]）
- ✅ Qt6 on OHOS：`QMAKE_HOST.os == 'HarmonyOS'`，`qt_functions.prf` 不识别 → 任何含 `CONFIG += testcase` 的 `.pro` qmake 直接 `Project ERROR: Operating system not supported.`（[knowledge_ref: notes.md#findings-7]）

---

*编译结束（close-archive marker 见 `.build-closed`）。*

**编译结束**: 2026-10-10
**最终状态**: built
