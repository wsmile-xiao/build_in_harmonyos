# knotifications5 5.116.0 适配笔记

## 背景

knotifications 是 KDE Frameworks 的桌面通知库。本条目为 KF5 分支
（libKF5Notifications.so），从 KF6 knotifications 6.26.0 配方改写，
适配 KF5/Qt5 链（kcoreaddons5/kconfig5/kwindowsystem5 5.116.0 已发布，
kconfig5 上架时点见下文"依赖时序"）。

## 依赖图（KF5 链现状）

```
knotifications5 5.116.0
├── qt5-qtbase/5.15.2.2 (override, 统一 kcoreaddons5 声明的 5.15.2)
│   └── 提供 Qt5Core/Gui/Widgets/DBus 组件 config（CMakeDeps + 包内原生 lib/cmake/Qt5）
├── kcoreaddons5/5.116.0  (KPluginFactory/KPluginMetaData)
├── kconfig5/5.116.0      (KSharedConfig/KConfigGroup)
└── kwindowsystem5/5.116.0 (KWindowSystem, 其 binary 基于 qt/5.15.19，
                             Qt 5.15 内 ABI 兼容，运行时经 SONAME 解析)
```

注意：kwindowsystem5 的 recipe 依赖 qt/5.15.19（完整 OHOS Qt5，-no-dbus）。
knotifications5 不能同时 requires qt/5.15.19.1（与 kwindowsystem5 的
5.15.19 同名冲突），也不能用 qt5-qtbase 与 qt/5.15.19 的 find_package 线
混合（CMakeDeps 的 Qt5Config 会遮蔽原生 config）。最终方案：**全部
find_package 走 qt5-qtbase 的 Qt5Config**（CMakeDeps 组件 config），
kwindowsystem5 的 binary 传递依赖 qt/5.15.19 仅作运行时 SONAME 解析。

## OHOS 适配要点

1. **Qt5DBus 不可用**：OHOS 的两个 Qt5 包都不提供真实 Qt5DBus 库
   （qt/5.15.19 构建带 -no-dbus；qt5-qtbase 的 CMakeDeps config 声明了
   Qt5::DBus 组件 target 但消费端无法解析 Qt5DBusConfig）。处理：
   - patch 0001：顶层 CMakeLists 的两处 REQUIRED DBus find_package 改
     `if (FALSE)`；**HAVE_DBUS 赋值段的 `if (TARGET Qt5::DBus)` 也强制
     FALSE**——否则 install(EXPORT) 生成的 KF5NotificationsConfig.cmake
     会烤进 `find_dependency(Qt5DBus)`，消费端 test_package 直接挂。
   - patch 0002：src/CMakeLists 四处 `if (TARGET Qt5::DBus)` 守卫强制
     FALSE（CMakeDeps 定义的 Qt5::DBus target 会误开这些守卫，拉入
     DBus-only 源码但缺 Qt5DBus 头文件/API）。
   - patch 0003：tests/CMakeLists 同守卫关闭（DBFus 测试可执行全部
     不再配置）。
   - patch 0004：knotificationmanager.cpp 的 Popup 插件 include/实例化
     加 `QT_DBUS_LIB` 守卫（上游 #else 分支假定非 Android/Mac/Win 必有
     DBus）；无 DBus 时 Popup 动作降级为 NotifyByTaskbar。
   - Canberra/Phonon4Qt5（音频通知后端）同段禁用——ohpcd 无此包。
2. **poqm 翻译禁用**：ecm_install_po_files_as_qm 需要 Qt5LinguistTools
   （lrelease），打包的 OHOS Qt5 不带。KF5 链兄弟件全部同样处理。
3. **examples/ 跳过**：需要 Qt5 Quick（qtdeclarative），未发布。
4. **CMAKE_SYSTEM_NAME=Linux 强制**：OHOS CMake 平台无 Platform/HarmonyOS
   模块，UNIX 变量不设置会导致 KDE if(UNIX) 源码选择丢源（kcoreaddons5
   先例）。R32 安全：OHOS POSIX 兼容。
5. **SONAME 注入**：OHOS（Generic）CMake 平台无 soname 规则，需手动注入
   CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG（E330，CI L5a 门禁）。
6. **ELF 自签名**：本地构建的 .so 带的 lld 占位签名在设备 loader 下被拒
   （dlopen: Permission denied），package() 末尾用 binary-sign-tool 重签
   全部安装 ELF（qt/5.15.19 配方先例）。
   - 实测：制品仓下载的 kcoreaddons5 包在本机 loader 下同样 Permission
     denied（其 GPG/发布签名在本机开发上下文不可验证），本地重建后
     （lld 占位签名）反而可加载——CI 环境与此相反（远端 release 会重新
     sign），本地验证时全部依赖本地建。
7. **/system/lib64 prepend**：sandbox 的 LD_LIBRARY_PATH 含不兼容
   libc++_shared.so，configure/install/test 前置 /system/lib64（kconfig
   6.26.0/kcoreaddons5 先例）。

## 上游测试口径（rule4）

上游默认形态的 CTest add_test 注册数：**0**（本 feature set）：
- autotests/KNotificationTest：上游注释掉（需 DBus session bus +
  fake_notifications_server）
- tests/ 全部 5 个可执行（kpassivepopuptest/knotificationrestrictionstest/
  unitylaunchertest/kstatusnotifieritemtest/knotificationdbustest）：
  `if (TARGET Qt5::DBus)` 守卫内，DBus 关闭后 0 注册
- examples/：手动示例可执行（无 add_test）

ctest 以 `--no-tests=ignore` 跑（0 注册是 feature set 的真实状态），
消费端测试（test_package）验证 KNotification API 表面。

## 依赖时序（W0 记录）

- kcoreaddons5/5.116.0：制品仓 2026-09-23 05:04 上架 ✅
- kwindowsystem5/5.116.0：制品仓 2026-09-20 10:24 上架 ✅
- kconfig5/5.116.0：main 已 merge（PR #10955，2026-09-23 18:59），
  制品仓 release 构建在途（REL-012 #8444）。本地验证用 main 归档配方
  自建（lld 占位签名可加载）。

## 踩坑记录

1. CMakeDeps 生成的 Qt5Config.cmake（qt5-qtbase）会遮蔽包内原生
   lib/cmake/Qt5 —— 若配方/test_package 声明 `generators = "CMakeDeps"`，
   find_package(Qt5) 命中的 CMakeDeps 版不含组件 include dirs
   （qt5-qtbase_Qt5_Core_INCLUDE_DIRS_RELEASE 为空），消费端编译缺
   Qt 头。**解法：test_package 不声明 CMakeDeps，手写
   conan_cmakedeps_paths.cmake PREPEND qt5-qtbase 包内 lib/cmake**
   （kconfig5 test_package 先例）。
2. install(EXPORT) 的 config 会把构建时的 target 状态烤进模板
   （HAVE_DBUS/HAVE_KWINDOWSYSTEM 等），守卫必须在构建前关闭而非仅
   依赖运行时宏。
3. 双 Qt5 包并存（qt/5.15.19 与 qt5-qtbase）在 conan 图中合法（不同
   ref），但 find_package 只能解析一条线；链接产物 NEEDED 全是 SONAME，
   运行时统一解析（Qt 5.15 minor 内 ABI 兼容）。
