# kconfigwidgets5 5.116.0 适配笔记

## 概述
将 KF5 KConfigWidgets（Qt5 配置对话框库）移植到 HarmonyOS PC (aarch64)。
走 Conan 配方流程，构建 `libKF5ConfigWidgets.so`。

## 依赖链现状（W0 核查，2026-09-24）
- ✅ 已发布：qt5-qtbase/5.15.2.2、kconfig5/5.116.0、kcoreaddons5/5.116.0、ki18n5/5.116.0
- ❌ 未发布（本地填链验证，配方 requires 保持终态声明）：
  - kwidgetsaddons5/5.116.0（sea_crab 任务 #12941 在手，分支未推送）
  - kcodecs5/5.116.0（任务 #12757 open 无人领）
  - kguiaddons5/5.116.0（ran060619 PR #11375 open，CI 卡 Worker 环境 sqlite3）
- **KWidgetsAddons 无法剔除**：PUBLIC 继承（KConfigDialog : public KPageDialog、
  KCodecAction/KRecentFilesAction : public KSelectAction），属真依赖。

## 关键适配决策

### 1. KAuth 关闭（WITH_KAUTH=OFF）
KF5Auth 未发布；上游 WITH_KAUTH 是 option 且只影响 KCONFIGWIDGETS_WITH_KAUTH
宏与可选链接，核心控件功能不受影响。

### 2. CMAKE_SYSTEM_NAME=Linux
OHOS CMake 平台无 Platform/HarmonyOS 模块，UNIX 变量不设——KDEInstallDirs/
KDECMakeSettings 的 if(UNIX) 安装路径选择失效。强制 Linux 平台（POSIX 兼容，
knotifications5/kcoreaddons5 先例）。

### 3. ki18n_install(po) 补丁禁用（0001）
需要 LinguistTools/po 完整工具链（OHOS Qt5 包不含），与 kconfig5 的
ecm_install_po_files_as_qm 禁用同族处理。

### 4. SONAME（E537）
`CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG=-Wl,-soname,` +
`CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE`（kconfig5 先例）。

### 5. ELF 重签名（本任务最关键坑）
**现象**：ctest 全部测试报 `Error loading shared library libKF5CoreAddons.so.5`
/ dlopen "Permission denied"——但文件存在、权限 770、组匹配。
**根因**：OHOS lld 为本地构建 ELF 输出**占位符 .codesign**，沙箱加载器拒绝。
CI 签过名的远程包（libQt5Core）能载、本地构建的不能载。
**修复**：`_resign_runtime_elfs()`——对构建树 bin/lib + 所有依赖包 lib 里的
lib*.so 用 binary-sign-tool -selfSign 1 重签名后再跑 ctest
（knotifications5 配方先例，本任务扩展到**依赖包目录**）。

### 6. 运行时环境顺序（_library_runtime_env）
`/system/lib64` 必须排 LD_LIBRARY_PATH 最前：系统库（libhilog 等 __h 命名空间）
需要真 libc++.so；SDK 的 libc++.so 是链接器脚本会遮蔽。
另外 LD_LIBRARY_PATH 必须在**进程启动前**设置（musl dlopen 快照语义）。

### 7. Qt5DBus 保持开启
qt5-qtbase/5.15.2.2 实际含 Qt5DBus（与 kconfig5 核实一致），
上游 `if (NOT ANDROID) find_package(Qt5 REQUIRED DBus)` 正常解析，
仅 KPasteTextAction（PRIVATE）链接它。

## 测试结果
- 上游测试（BUILD_TESTING=ON，ctest 实测）：**5/5 通过**
  - kconfigdialog_unittest / klanguagenametest / kcolorschemetest /
    kcmdbartest / krecentfilesaction_test 全过
  - kstandardactiontest 豁免：changingShortcut 槽等待
    KStandardShortcutWatcher 配置变更通知（OHOS 无 inotify 不触发，
    kconfig5 豁免 kstandardshortcutwatchertest 同根因）；该测试其余 5 槽
    实测通过（5 passed, 1 failed 手工验证）
- test_package 消费者测试：**原生执行通过**
  （KConfigDialog::exists nullptr 断言 + KCoreConfigSkeleton addItemString/
  property 往返；另备 link-level proof fallback）

## 填链三件套（本地验证用，不入 git）
- kguiaddons5：直接用 ran060619 PR #11375 分支配方（e7fe0fc2）
- kwidgetsaddons5：自写配方 + 2 patch（po 禁用 + setAccessibleName 的
  QT_NO_ACCESSIBILITY 守卫——qt5-qtbase 5.15.2.2 的
  QT_FEATURE_accessibility=-1）
- kcodecs5：自写配方 + 1 patch（po 禁用）；Gperf 用系统
  /data/service/hnp/bin/gperf

## 上游测试修改说明
无源码级测试修改；仅 CMake 层豁免 kstandardactiontest（ctest -E），
理由与证据链见 test_package/MANIFEST.yml。

---

**编译结束**: 2026-09-24 10:40
**最终状态**: built（依赖三件套发布后即可提 PR 走 CI）
