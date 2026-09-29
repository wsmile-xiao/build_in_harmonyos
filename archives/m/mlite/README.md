# mlite 0.5.5 for HarmonyOS

## 概述

mlite 是 Sailfish OS（源自 MeeGo Touch）的一组实用类库：桌面条目解析（MDesktopEntry）、
通知与通知组（MNotification/MNotificationGroup）、远程动作（MRemoteAction）、
权限（MPermission）、文件数据存储（MFileDataStore），并附带两个命令行工具
（mlitenotificationtool / mliteremoteaction）。本目录记录其在 HarmonyOS PC（OHOS aarch64）
上的 Conan 配方与验证结果。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | mlite |
| 版本 | 0.5.5 |
| 上游 | https://github.com/sailfishos/mlite （tag `0.5.5` → `42c3b2102dadfc54a2cc7c87c6e4cfb28437c908`） |
| 源码 | https://github.com/sailfishos/mlite/archive/refs/tags/0.5.5.tar.gz |
| 许可证 | LGPL-2.1-or-later |
| 构建系统 | qmake（Qt5） |
| 语言 | C++（Qt5） |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS / OpenHarmony（aarch64，HongMeng Kernel） |
| 编译器 | clang/clang++ 15.0.4（OHOS SDK） |
| Profile | `ci/conan/profiles/ohos-aarch64`（os=OHOS, arch=armv8, libc++, cppstd=17） |

## 依赖

| 依赖 | 版本 | 类型 | 来源 |
|------|------|------|------|
| qt5-qtbase | 5.15.2.2 | 链接（Qt5Core + Qt5DBus） | 上游 `src/src.pro:17 QT = core dbus`、`src/mlite5.pc.in:11 Requires: Qt5DBus` |
| glib | 2.84.0 | 链接（仅满足上游无条件 `PKGCONFIG += glib-2.0`） | 上游 `src/src.pro:22` |
| dbus / expat / zlib / libffi / pcre2 | 1.14.10 / 2.8.2 / 1.3.1 / 3.4.4 / 10.40 | 传递 | qt5-qtbase、glib |

**构型说明**：采用上游原生的 **dconf 关闭构型**（`src/src.pro` 的 `packagesExist(dconf)` 为假，
上游会打印 `warning("dconf not found; MDConfItem will not be built")`），因此本包不含
MGConfItem / MDConfItem / MDConfGroup。原因见 `0.5.5/notes.md` 与 `0.5.5/reports/test-report.md`：
制品仓 `dconf/0.40.0` 预编译二进制在 OHOS 上无法加载（ELF 自签名失效），且 glib 仅静态库会
与 dconf 形成同进程双 GLib 实例导致崩溃。

## 消费与产物

- 库：`lib/libmlite5.so.0.5.5`（SONAME `libmlite5.so.0`）
- 头文件：`include/mlite5/`（`#include <MDesktopEntry>` 风格，与上游 `mlite5.pc` 的 `-I` 一致）
- 可执行：`bin/mlitenotificationtool`、`bin/mliteremoteaction`（见软件级 `commands.json`）
- pkg-config：`mlite5`（Conan 生成，`Requires: Qt5Core/Qt5DBus`）
- CMake：`find_package(MLite CONFIG REQUIRED)` → 目标 `MLite::MLite`

## 已知限制

1. QtDBus 在本平台运行期不可用：`qt5-qtbase` 以 `-dbus`（运行期 `dlopen("libdbus-1")`）构建，
   而制品仓 `dbus` 仅提供静态 `libdbus-1.a` → 依赖 D-Bus 的连接类功能需待依赖侧修复
   （dbus 出 shared 构型或 qt5-qtbase 改 `-dbus-linked`）。
2. 上游 `tests/` 需 Qt Linguist（`lrelease`）才能构建，本配方不构建上游测试；上游测试实测结果
   见 `0.5.5/reports/test-report.md`。
3. 产物 RUNPATH 记录构建期 Conan 缓存路径（qtbase mkspec 固有行为，与 `archives/l/libngf-qt` 一致）；
   消费方通过 Conan 生成的运行环境解析 Qt5。OHOS 下不可事后修改 ELF（会破坏代码签名导致拒载）。
