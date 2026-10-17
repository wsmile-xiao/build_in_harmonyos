# kauth5 5.116.0 适配笔记

> KF5 系列（Qt5 版）kauth，与已有的 kauth/6.x (KF6) 归档分开。
> 参考配方：kcoreaddons5/5.116.0、kwidgetsaddons5/5.116.0（同依赖 qt5-qtbase + ecm）。

## 编译环境
- 构建系统: cmake (Ninja via cmake_layout)
- 编译日期: 2026-10-03
- 编译器: clang/clang++ (OHOS toolchain, profile ohos-aarch64)
- 设备: HarmonyOS aarch64（原生构建，非交叉编译）

## 源码校验
- 官方 URL: `https://download.kde.org/stable/frameworks/5.116/kauth-5.116.0.tar.xz`
- SHA256（本机实测）: `ace1ee1ac0aa1b291c4c50c93fc3503b62318eeef0df0ee394a5a08da9691ff4`
- 大小: 2307868 bytes

## 上游测试清点（R51 三步法第 1 步）

`autotests/CMakeLists.txt` 在 `BUILD_TESTING=ON` 且 `Qt5::Test` 存在时注册：

| ctest 名 | 来源 | OHOS 状态 |
|---|---|---|
| `KAuthSetupActionTest` | autotests/SetupActionTest.cpp | 注册并运行 |
| `KAuthHelperTest` | autotests/HelperTest.cpp + TestHelper.cpp | 注册；需要 session bus |
| `KAuthPolicyGenTest` | autotests/foo_actions.actions（kauth-policy-gen 可执行） | **不注册**（`if(NOT KAUTH_BACKEND_NAME STREQUAL "FAKE")`） |
| `KAuthPolicyGenTestCompare` | 同上（compare_files） | **不注册**（同上） |

即：上游可发现 4 项，FAKE 后端下实际注册 2 项。

## 适配要点

- **KAUTH_BACKEND_NAME=FAKE / KAUTH_HELPER_BACKEND_NAME=FAKE**：KAuth 的原生后端是
  PolkitQt-1，未发布到 ohpcd（`conan download polkit-qt-1/* -r=ohpcd --only-recipe` 未命中），
  且运行还需 polkit daemon。上游 `src/ConfigureChecks.cmake` 在探测不到 PolkitQt 时本就
  回退 `FAKE`，这里显式固定同一决策，避免依赖系统探测结果。副作用：`kauth-policy-gen`
  与两个插件 MODULE 目标不构建，`KAuthPolicyGen*` 两项 ctest 不注册（其 add_test 位于
  同一 guard 内）。`KF5::AuthCore` / `KF5::AuthWidgets`、头文件与 `KF5AuthConfig.cmake`
  正常提供。
- **QT_MAJOR_VERSION=5**：ECM 6.20 >= 5.240，`QtVersionOption.cmake` 在尚无 Qt target 时
  默认 `BUILD_WITH_QT6=ON`，会让上游 `find_package(Qt${QT_MAJOR_VERSION} ...)` 去找 Qt6。
  必须显式固定（kcoreaddons5 / kwidgetsaddons5 先例）。
- **KF_IGNORE_PLATFORM_CHECK=TRUE**：OHOS 不在 KDE 平台白名单（metainfo.yaml）内。
- **qt5-qtbase 用 5.15.2.2**：只有 5.15.2.2 起才提供 `Qt5Widgets` / `Qt5DBus` 组件
  （上游需要 `find_package(Qt5 ... Widgets)` 与 `find_package(Qt5DBus CONFIG REQUIRED)`）。
  `kcoreaddons5/5.116.0` 声明的是 `qt5-qtbase/5.15.2`，故用
  `self.requires("qt5-qtbase/5.15.2.2", override=True)` 统一版本族（KDE 迁移固定的依赖
  版本族不匹配模式，同 kauth/6.26.0 对 qtbase 的 override 做法）。override 只改写引用：
  kcoreaddons5 已发布的二进制记录的依赖是 `qt5-qtbase/5.15.Z`，仍是命中缓存/制品仓，
  不会触发重建。
  注意：Conan 不允许「同一 conanfile 既直接 requires 又 override 同名包」
  （`Duplicated requirement`），因此 qt5-qtbase 只以 override 形式出现。
- **Qt5 target 解析走 qt5-qtbase 自带 native cmake 配置**：该包是 qmake/configure 产物，
  自带完整 `lib/cmake/Qt5*`、`bin/moc|rcc|uic`、`Qt5*Macros.cmake`、`include/QtDBus`。
  与 kwidgetsaddons5 不同，这里**不用** CMakeDeps 重建 Qt5Config，而是把包前缀与
  qt5-qtbase 自带 `share/ECM` 树（以及 ecm 的 `cmake`/`share/ECM/*`）前置到
  `CMAKE_PREFIX_PATH` / `CMAKE_MODULE_PATH`，使上游的 config 模式 find_package 直接命中。
- **ecm_install_po_files_as_qm(poqm) 打补丁关闭**：qt5-qtbase 未提供 Qt5LinguistTools
  （lconvert/lrelease）。与 kcoreaddons5 / kwidgetsaddons5 / kconfig5 同一补丁。
- **SONAME 显式提供**：HarmonyOS 未映射到 Linux CMake 平台，`CMAKE_SHARED_LIBRARY_SONAME_*_FLAG`
  为空会导致产物无 `DT_SONAME`（CI L5 门禁）。按 kwidgetsaddons5/attica5 已验证模式显式设置
  `-Wl,-soname,`。
- **dbus session bus**：`KAuthHelperTest` 通过 session bus 驱动 `DBusHelperProxy`。
  `qt5-qtbase/5.15.2.2` 经 `dbus/1.14.10` 依赖引入了 `bin/dbus-daemon`，配方会优先使用
  它启动私有 session bus（`--fork --print-address`），并在测试后回收进程；找不到 daemon 时
  按排除处理并明文告警，**绝不计为通过**。
  > 环境语义可迁移性（W0b）：kauth/6.26.0 的 notes 记录「ohpcd 的 dbus 只有客户端库、无
  > dbus-daemon」，本任务实测该结论在当前环境**不成立**（5.15.2.2 依赖的 dbus 包内含
  > `bin/dbus-daemon`、`bin/dbus-run-session`），故 KAuthHelperTest 得以真实运行。
- **测试运行环境**：`QT_QPA_PLATFORM=offscreen` + 独立的 `HOME`/`XDG_RUNTIME_DIR`
  （kwidgetsaddons5 headless 模式）。

## 关键命令

```bash
# 源码获取与校验
curl -fsSL -o kauth-5.116.0.tar.xz \
  https://download.kde.org/stable/frameworks/5.116/kauth-5.116.0.tar.xz
sha256sum kauth-5.116.0.tar.xz
# ace1ee1ac0aa1b291c4c50c93fc3503b62318eeef0df0ee394a5a08da9691ff4

# 本地验证
# conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -r=ohpcd --build=missing
```
---

**编译结束**: 2026-10-03 22:51
**最终状态**: built
