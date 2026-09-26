# kteatime 26.04.0 适配说明（HarmonyOS PC）

## 概览
KDE Gear 泡茶计时器（纯 Qt6 Widgets GUI 应用），单可执行 `kteatime`（约 1100 行
C++），无测试目录/测试目标。源码：`https://download.kde.org/stable/release-service/26.04.0/src/kteatime-26.04.0.tar.xz`。

## 依赖
- Qt6 ≥ 6.7.0：qtbase/6.11.1（Core、Widgets）
- KF6 ≥ 6.3.0（仓内 6.14.0 现成）：Config/CoreAddons/Crash/GuiAddons/I18n/
  IconThemes/Notifications/TextWidgets/XmlGui
- ECM 6.20.0（tool_requires）
- **裁减**：KF6::StatusNotifierItem、KF6::NotifyConfig（见下）

## 关键适配点
1. **0001 补丁（裁减 DBus 依赖组件）**：Qt6 DBus 未发布到 ohpcd（qtbase
   `FEATURE_dbus=OFF`，knotifications/kxmlgui 配方均 `USE_DBUS=OFF`）。
   `KStatusNotifierItem`（KF6::StatusNotifierItem）本质是 StatusNotifierWatcher
   的 DBus 客户端，且 OHOS 无系统托盘；`KNotifyConfigWidget`（KF6::NotifyConfig）
   为通知配置对话框、同样依赖 DBus。二者裁减：`TopLevel` 基类
   KStatusNotifierItem → QWidget，托盘 API（setStatus/setIconByName/
   setOverlayIcon*/showMessage/setTooltipText）为 no-op，移除『配置通知』菜单项；
   通知由 `KNotification::event` 承担（knotifications/6.14.0 仓内、无 DBus 时
   优雅降级）；根/子 CMakeLists 移除两个组件。菜单/计时/通知/配置逻辑全保留。
2. **构建变量**：`KF_IGNORE_PLATFORM_CHECK=TRUE`（OHOS 不在 KDE 平台列表）、
   `USE_DBUS=OFF`、`KF_SKIP_PO_PROCESSING=ON`（lconvert 在本平台加载
   libQt6Core 失败，.qm 翻译目录非必需，同 ktextwidgets 配方）。
3. **CMake 查找路径**：ECM_MODULE_PATH 手工设置（CMakeDeps 生成的
   ECMConfig.cmake 不传播，KDEInstallDirs/KDECMakeSettings 等 KDE 模块依赖它，
   同 kxmlgui 配方）；`conan_cmakedeps_paths.cmake` 把 qtbase 及全部依赖的
   lib/cmake 加入 CMAKE_PREFIX_PATH（qtbase 用 cmake_find_mode=none，
   find_package(Qt6 CONFIG) 才可解析）。
4. 平台保护：0001 补丁仅 OHOS 应用，其它平台不受影响。

## 路径判定：路径 A（基础适配）
- 路径 C 四条件均不满足：① 无强绑定 Linux 私有系统接口（纯 Qt Widgets GUI）；
  ② 无私有编译工具链（标准 CMake+ECM，仓内 KF6 构建链已打通）；③ 无汇编/
  闭源/特殊调度；④ 依赖链 10 个 KF6 组件 + Qt6 全部仓内现成且版本满足
  （≥6.3.0），上游测试 0 个、校验成本极低。
- 路径 B 不成立：无跨库可复用的新诊断模式（裁减 DBus 组件遵循仓内
  USE_DBUS=OFF 既有先例），无知识增量。

## 测试
- **上游测试：0 个**（无 tests/ 目录、无 *test* 源文件、CMakeLists 无 test
  目标），MANIFEST 如实申报 0/0（不虚报不伪造）。
- **适配后补全**：test_package smoke test——`QT_QPA_PLATFORM=offscreen`
  `timeout 30 kteatime --version`（KAboutData 打印版本退出 0，真实运行安装后
  二进制，验证可执行 + Qt6/KF6 依赖解析；offscreen 平台插件随 qtbase 安装，
  qtbase 配方自身测试同款设置）。

## 本地验证
- conanfile.py / test_package conanfile.py：py_compile 通过
- conandata.yml / MANIFEST.yml / manifest.yaml：YAML 解析通过
- 0001 补丁：对上游源码 `patch --dry-run` 应用通过（4 文件 195 行）
- 完整 OHOS 构建：由 CI 执行（本机 conan 为基线 2.29.1，无法运行
  ohos-aarch64 profile）
