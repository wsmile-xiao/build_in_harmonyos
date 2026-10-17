# libkysdk-kabase 3.0.1.0 HarmonyOS PC 适配笔记

## 概述
- 包名：`libkysdk-kabase`；版本：`3.0.1.0`（= 上游 huanghe 分支版本，debian/changelog `3.0.1.0-ok0.29`）
- 上游：`https://gitee.com/openkylin/libkysdk-applications`（openKylin 官方源）
- 源：huanghe 分支 HEAD 提交 `621ebd9dd72c7aa2e6642e2cd929e2b13c25b1e4`
  - 归档 URL（提交级，不可变）：
    `https://gitee.com/openkylin/libkysdk-applications/repository/archive/621ebd9dd72c7aa2e6642e2cd929e2b13c25b1e4.tar.gz`
  - sha256：`f4877743fced6e0e5b2e68a5004acfb008d1f9b5b555e3dc1d326659a0c1cc97`
- 构建系统：qmake（Qt5）；只构建 `kysdk-kabase/kabase/single_application` 组件
- 产物：`lib/libkysdk-kabase.so`（`TARGET = kysdk-kabase`）+ `include/single_application/single_application.hpp`
- 与兄弟包 `archives/l/libkysdk-applications/3.0.1.2`（同上游，Debian pool 源，版本 3.0.1.2）
  的区别：本包名与目录 slug 时 `libkysdk-kabase`，只提供 single_application 组件，
  供 kylin-calendar 的 `#include <single_application/single_application.hpp>` 直接消费。

## 头文件提供者调查（编排方独立核验证据 + 本次复核）
消费者 `kylin-calendar/lunarcalendarwidget/main.cpp:23` 使用
`#include <single_application/single_application.hpp>`。上一版曾用
`itay-grudev/SingleApplication` 并把 `singleapplication.h` 改名 shim 成
`single_application.hpp` —— **错误身份，已废弃**（该库无 `kdk::kabase::QtSingleApplication`，
且是 8.3.0 非单例化 API）。

真实提供者 = **`kysdk-kabase`**（属于上游 `gitee.com/openkylin/libkysdk-applications`）。实测证据：

| 检查 | 命令 / URL | 结果 |
| --- | --- | --- |
| 头文件存在 | `https://gitee.com/openkylin/libkysdk-applications/raw/openkylin/yangtze/kysdk-kabase/kabase/single_application/single_application.hpp` | http=200, **4056 bytes**（yangtze）；huanghe 同文件 4122 bytes（多 5 行 doxygen 注释） |
| 命名空间/类型 | 头文件内容 | `namespace kdk { namespace kabase { class QtSingleApplication : public QApplication; }}` |
| 实现文件 | 同目录 `single_application.cpp` | http=200, 12069 bytes（yangtze）/ huanghe 同（`#include "local_peer.hpp"`，原引 `<kwindowsystem.h>` 调 `KWindowSystem::forceActiveWindow`） |
| 消费者 CMake | `kylin-calendar/CMakeLists.txt:51-53` | `pkg_check_modules(KYSDKUKUIWINDOWHELPER_PKG REQUIRED kysdk-ukuiwindowhelper)` |
| 消费者 CMake | `kylin-calendar/CMakeLists.txt:76-79` | `pkg_check_modules(KYSDKKABASE_PKG …)` + `link_libraries(kysdk-kabase.so)` |
| 消费者源码 | `lunarcalendarwidget/main.cpp:23` | `#include <single_application/single_application.hpp>` |

补充：`main.cpp` 全文 126 行，**仅 include 该头，未调用任何 SingleApplication/QtSingleApplication API**
（单例检测实际走 `w.checkSingle(strList)`）。即消费者对该包的硬需求是**头文件 + 链接可用**，
库本身须真实存在且导出对应符号（本包提供）。

## single_application 组件依赖分析（三段式结论）
1. **组件内依赖（无外部系统库）**：4 个源文件
   `single_application.cpp / local_peer.cpp / locked_file.cpp / locked_file_unix.cpp`，
   include 链仅 Qt（`QApplication/QWidget/QObject/QCoreApplication/QDataStream/
   QRegularExpression/QTime/QLocalServer/QLocalSocket/QFile/QVector`）+ 标准 C 头
   （`string.h/errno.h/unistd.h/fcntl.h/sys/types.h/time.h`）。
   → 需要 Qt5 **Core + Network（QtLocalPeer 用 QLocalServer/QLocalSocket）+ Widgets**。
2. **唯一平台硬点**：`single_application.cpp:45 #include <kwindowsystem.h>` 与
   `:326 KWindowSystem::forceActiveWindow(actWin->winId())`（OHOS 无 X11/KWin）。
   → 补丁 0002 改用 Qt 原生 `actWin->raise(); actWin->activateWindow();`（非空壳，实质移植）。
3. **其余 kabase 子模块（gsettings-qt/QGSettings、kylin_system、kylin_image_codec/stb、
   opencv/freeimage、libkylog/kyconf、X11/xcb、KWindowSystem、systemd）依赖链 OHOS
   制品仓不可得** → `kabase.pro` 裁剪为仅 single_application（补丁 0001），
   与兄弟包 `archives/l/libkysdk-applications/3.0.1.2` 补丁 0001「把 kysdk-kabase 模块整体裁掉」
   同一理由。

## 依赖（制品仓可用性，W0）
| 依赖 | 可用性 | 处理 |
| --- | --- | --- |
| qt5-qtbase/5.15.2.2 | ✅ 制品仓（已实测可消费） | qmake + Qt5 Core/Network/Widgets |
| gsettings-qt（QGSettings） | ❌ 无配方 | 随 kabase 其余模块裁剪 |
| opencv / freeimage / stb | ❌ 无 | 随 kylin_image_codec 裁剪 |
| X11/xcb / KWindowSystem / x11extras | ❌ 无 | kabase.pro 去 x11extras/KWindowSystem；源码 0002 去 KWindowSystem |
| systemd / kylog / kyconf | ❌ 无 | 随 kabase 其余模块裁剪 |
→ 结论：**本包仅需 qt5-qtbase/5.15.2.2**，其余全部经裁剪移除（非 stub 伪装）。

## 补丁集（0001-0002，diff -u 生成，strip=1）
- **0001-kabase-pro-single-application-only.patch**：`kysdk-kabase/kabase/kabase.pro`
  重写为仅构建 single_application 组件——`QT += core network widgets`、`TARGET = kysdk-kabase`、
  `TEMPLATE = lib`、`CONFIG += c++11 console no_keywords`，HEADERS/SOURCES 只列
  single_application 的 3 头 + 4 源；删除 `-lsystemd -lkylog -lkyconf -lopencv_* -lfreeimage* -lstb`、
  `PKGCONFIG += gsettings-qt openssl x11`、`QT += x11extras KWindowSystem` 及
  opencv/kysdk-base 的 INCLUDEPATH。
- **0002-single-application-drop-x11-kwin.patch**：`single_application.cpp`
  去 `#include <kwindowsystem.h>`，`KWindowSystem::forceActiveWindow(actWin->winId())` →
  `actWin->raise(); actWin->activateWindow();`（Qt 原生窗口激活）。

> 说明（为何不用 refresh-patch --auto）：本任务为首次适配、无历史构建日志；两个补丁以
> `diff -u` 从干净源码树副本（orig/ 与 mod/）生成，strip=1（`a/`、`b/` 前缀），
> 与兄弟包补丁生成方式一致。

## R51 上游测试三步法
### 第一步：清点上游测试（证据）
`kysdk-kabase/test/`（huanghe @3.0.1.0）：
- `kabase_test.pro`（`TEMPLATE = app`）+ `main.cpp` + `{dbus,gsettings,image,widget}_test.{hpp,cpp}`
  —— **手动测试台**：`main.cpp` 里手工调用各接口（多为注释开关切换），**无 ctest/QTest 自动注册**。
  依赖 `-lopencv_core/imgcodecs/imgproc`、`gsettings-qt`、`dbus` 及被裁模块 → OHOS 不可构建。
- `application_access_test/{application_a,application_b}` —— 单例示例应用（`TEMPLATE=app`），非自动化测试。
- **single_application 组件**：`test/main.cpp` 的 `main()` 中“应用单例测试”整段被注释
  （`// kdk::kabase::QtSingleApplication app(argc, argv); ... return app.exec();`），
  手动/交互式（需真实显示与交互）。
- **自动化测试目标数 N = 0**（kysdk-kabase 无 single_application 组件的自动化用例）。

### 第二步：可运行环境实际运行
- 上游自动化用例 N = 0（无可运行项）——**具体技术原因**：single_application 无自动化测试；
  唯一测试台 `kabase-test` 依赖 opencv/gsettings-qt/dbus 与被裁模块（本包按需裁剪），
  且为手动交互式而非 ctest。**非“没环境”，是上游确无该组件自动化测试**（清点证据见上/MANIFEST.yml）。
- 本包补足：`test_package` 用 qt5-qtbase 的 qmake 编译消费者程序，**真实调用被测包 API**
  （`QtSingleApplication` 构造 / `id()` / `activationWindow()`/`setActivationWindow()` / `isRunning()`），
  在 `QT_QPA_PLATFORM=offscreen` + 可写 `TMPDIR` 下运行（OHOS `/tmp` 只读，QtLocalPeer 的
  `.lockfile` 需可写临时目录）。

### 第三步：如实回填
- 上游 N = 0（无 single_application 自动化用例）；N′（可运行）= 0；上游通过率 = N/A（无用例）。
- 本包 test_package 实测结果见 `reports/`/`.ci-result.json` 与 `test_package/MANIFEST.yml`
  （消费者测试断言 3 项，真实运行，非占位符）。

## 排错要点
- qmake 构建依赖 qt5-qtbase 的 `qt.conf`/`.pri` 重定位（`_fix_qtbase_paths`，同 libkysdk-applications 先例）；
  `QTDIR`/`PATH` 经 Conan `Environment` 注入 build env。
- **gitee 归档端点的 WAF 按 User-Agent 判别（根因 + 修复）**：`repository/archive/<ref>.tar.gz`
  对 **curl/wget 类 UA** 返回 302→`blazearchive/...`（真实 tar.gz），对 **python-requests / Conan /
  浏览器 UA** 直接返回 HTTP 200 HTML 挑战页（sha256 不符）。conan 默认 UA = `Conan/<ver> (...)`，
  会被拦 → `get()` 连续报 `sha256 hash failed`（Computed hash 每次不同=挑战页）。
  修复：配方 `source()` 显式传 `headers={"User-Agent": "curl/8.0.0"}`（conan 的 `_add_kwargs`
  仅在**未提供** UA 时才注入默认值，故显式 UA 生效），并加大 `retry=5, retry_wait=20`。
  - 实测（同窗口对照）：UA `curl/8.0.0`/`curl/7.88`/`Wget/1.21` → 2398992 bytes（sha256
    `f4877743…` 命中）；UA `Python-urllib/3.12`/`python-requests/2.31.0`/`Conan/2.29.1`/`Mozilla/5.0`
    → 47853 bytes（挑战页）。修复后 `conan source .` → `Sources correctly downloaded`（RC=0）。
- **头文件安装路径**：上游 `single_app_headers.path = /usr/include/kysdk/applications/kabase/single_application/`；
  本包安装到 `include/single_application/single_application.hpp`，使消费者
  `#include <single_application/single_application.hpp>` 直接可用。这是**上游真实文件路径**，
  非 copyfile 改名 shim（文件名即上游 `single_application.hpp`）。
---

**编译结束**: 2026-10-08 20:12
**最终状态**: built
