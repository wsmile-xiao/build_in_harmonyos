# libkysdk-kabase

openKylin KylinSDK **kabase** 的 `single_application` 组件（HarmonyOS PC / arm64 适配）。

## 是什么
- 提供 `libkysdk-kabase.so` 与上游真实头文件 `include/single_application/single_application.hpp`。
- 头文件声明 `namespace kdk { namespace kabase { class QtSingleApplication : public QApplication; }}`，
  基于 `QtLocalPeer`（`QLocalServer`/`QLocalSocket`）实现应用单实例检测与消息转发。
- 是 `kylin-calendar` 的直接依赖（`lunarcalendarwidget/main.cpp:23`
  `#include <single_application/single_application.hpp>`；`CMakeLists.txt:76-79`
  `pkg_check_modules(KYSDKKABASE_PKG …)` + `link_libraries(kysdk-kabase.so)`）。

## 上游
- 仓库：<https://gitee.com/openkylin/libkysdk-applications>（openKylin 官方源）
- 分支 / 版本：`openkylin/huanghe` = `3.0.1.0`
- 源锁定：提交 `621ebd9dd72c7aa2e6642e2cd929e2b13c25b1e4`（归档 sha256 见 `3.0.1.0/conandata.yml`）
- 构建系统：qmake（Qt5）

## 适配要点
- 只构建 `kysdk-kabase/kabase/single_application` 组件（`kabase.pro` 裁剪，补丁 0001）：
  该组件自包含，仅需 Qt5 Core/Network/Widgets。
- 去掉唯一 X11/KWin 依赖（补丁 0002）：`single_application.cpp` 的 `<kwindowsystem.h>` /
  `KWindowSystem::forceActiveWindow` → Qt 原生 `raise()/activateWindow()`。
- kabase 模块其余部分（gsettings-qt/opencv/freeimage/X11/xcb/KWindowSystem/systemd/kylog/kyconf）
  依赖链 OHOS 制品仓不可得，随模块裁剪。
- 依赖：`qt5-qtbase/5.15.2.2`。

## 版本
| 版本 | 状态 | 源 |
| --- | --- | --- |
| 3.0.1.0 | built | gitee openkylin/huanghe @621ebd9 |

详见 `3.0.1.0/notes.md` 与 `3.0.1.0/manifest.yaml`。
