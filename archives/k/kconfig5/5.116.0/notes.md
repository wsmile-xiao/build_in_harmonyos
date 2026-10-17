# KConfig 5.116.0 HarmonyOS PC 适配笔记

## 概述
将 KF5 KConfig（Qt5 配置系统）移植到 HarmonyOS PC (aarch64)。走 Conan 配方流程，
依赖 `qt5-qtbase/5.15.2.2`（含 Qt5Xml）+ `ecm/6.20.0`，CMake/Ninja 构建。

## 关键适配决策

### 1. 依赖选择
- `qt5-qtbase/5.15.2.2`：**必须含 Qt5Xml**。KConfig 5.116.0 在 `src/gui` 与
  `src/kconfig_compiler` 硬依赖 `find_package(Qt5 REQUIRED Xml)`。plain `5.15.2`
  不含 Xml（W0 检查时误用，后更正为 5.15.2.2）。
- `ecm/6.20.0`：ECM 提供 KConfig 所需的 KF5 基础设施。ecm 找到 Qt5 时设
  `QT_MAJOR_VERSION=5`（KF5 关键变量）。

### 2. CMake 平台适配
- `KF_IGNORE_PLATFORM_CHECK=TRUE`：绕过 KDE 平台检测（OHOS 不在 KDE 平台列表）。
- `KCONFIG_USE_DBUS=ON`（与上游默认一致）：**qt5-qtbase/5.15.2.2 实际包含
  Qt5DBus**（`include/QtDBus` + `lib/cmake/Qt5DBus` + `libQt5DBus.so`），故 KConfig
  的 DBus 组件保持开启，`dbussanitizertest` 等 DBus 测试可运行
  （首稿误判为缺失而裁掉，属修正）。
- `KCONFIG_USE_QML=OFF`：KF5 选项名（KF6 为 `USE_DBUS`/`USE_QML`）。**仅 QML
  保持关闭**——`qt5-qtbase` 不含 Qt5Qml；制品仓虽有 `qt5-qtdeclarative/5.15.2`，
  但版本与 qtbase 5.15.2.2 不齐，且 KConfigQml 仅为 QML 集成辅助组件，非配置核心
  所需，引入会带来跨模块版本兼容风险。与 KF6 kconfig 6.26.0 一致口径。
- `KDE_INSTALL_USE_QT_SYS_PATHS=OFF`：避免 KConfig 安装到 Qt 系统路径。

### 3. SONAME（E537，关键坑）
OHOS CMake 平台模块**未定义 `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG`**，导致 KF5
`.so` 无 DT_SONAME。消费者链接后 `DT_NEEDED` 记录**路径形式**（如
`bin/libKF5ConfigCore.so`），loader 无法解析 → 运行时 `symbol not found`。
修复：在 `generate()` 设置
`CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG = -Wl,-soname,`，lld 即生成真实 soname。
> 参考实现 archives/a/accessibility/26.04.3（同一口径）。
> 不要用 CMAKE_SHARED_LINKER_FLAGS 手动 `-soname`（会污染多库构建，
> 链接 `--no-allow-shlib-undefined` 直接失败）。

### 4. ECM_MODULE_PATH 手动注入
CMakeDeps 生成的 ECMConfig.cmake 不传播 `ECM_MODULE_PATH`，而 KConfig 顶层
CMakeLists 直接引用该变量。在 `generate()` 从 ecm.package_folder 手动拼
`share/ECM/{modules,find-modules,kde-modules}` 注入。

### 5. Qt5 mkspecs compat（_prepare_qt_mkspec_compat）
qtbase 的 Xml/Gui CMake 引用的 mkspecs 路径在 `../b/mkspecs`，需将
`package_folder/mkspecs/linux-clang` 复制到 `os.path.dirname(package_folder)/b/mkspecs`。
（attica-kf5 同法。）

### 6. conan_cmakedeps_paths.cmake
qt5-qtbase `cmake_find_mode=none`，CMakeDeps 不把它 lib/cmake 加进
CMAKE_PREFIX_PATH，需手写该文件 prepend qtbase lib/cmake + ECM 路径。

### 7. poqm 补丁（patches/0001-CMakeLists.txt.patch）
`ecm_install_po_files_as_qm(poqm)` 依赖 Qt5LinguistTools（qt5-qtbase 未含），
以补丁注释掉。（同 KF6 kconfig 6.26.0 处理。）

### 8. 运行时库路径（_library_runtime_env + _prepare_ctest_runtime_links）
测试/工具运行时需把 qtbase lib、build bin/lib 与 build 根目录（含 compat bin 软链）
加入 LD_LIBRARY_PATH，并设 XDG/ HOME 到 build 下可写目录（OHOS 沙箱不可写）。

## 测试
- ctest 全量 46 个可执行测试：完整 HOME/XDG 环境实测 **43/46 直接通过**，
  仅 3 个排除（均有 OHOS 平台技术原因，见下）。
- 按审查方口径（上游 QTest 槽函数 98 个用例）：**94/98 通过**，4 个 OHOS
  环境性失败（kconfigtest 3 例 + kdesktopfiletest 1 例）。
  - kconfigtest 失败 3 例：`testFailOnReadOnlyFileSync`（OHOS 沙箱 chmod
    只读不生效 E046，sync() 不报错）、`testNotify`/`testNotifyIllegalObjectPath`
    （无 inotify，KConfigWatcher 事件不触发）。
  - kdesktopfiletest 失败 1 例：`testSuccessfulTryExec`（access(X_OK) 探测
    可执行恒 False，HMDFS chmod 固定 660，E524/E046 类）。
  - kstandardshortcutwatchertest：在 98 统计外，2/4 通过（kgobalaccel +
    session 事件循环不可用，缺失 2 例）。
- test_package 消费者 round-trip 1/1 通过。
- 详细见 reports/test-report.md。

## 工具
- kreadconfig5 / kwriteconfig5 → commands.json（R38，软件级）。
---

**编译结束**: 2026-09-18 13:19
**最终状态**: built
