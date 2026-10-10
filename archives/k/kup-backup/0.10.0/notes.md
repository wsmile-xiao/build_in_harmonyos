# kup-backup 0.10.0 适配笔记

## 基本信息
- KDE 备份方案（KF6/Qt6，GPL-2.0-or-later），上游 invent.kde.org/system/kup
- 上游 0.10.0 无 tests/ 目录（0 用例，MANIFEST 如实申报；test_package 冒烟 3 断言）

## 编译环境
- 构建系统: cmake (Conan 2.x recipe, conan create)
- 编译器: OHOS SDK clang 15 (profile ohos-aarch64, os=OHOS, armv8, libc++, cppstd=17)
- 源码: https://invent.kde.org/system/kup/-/archive/kup-0.10.0/kup-kup-0.10.0.tar.gz
  sha256 7942c68d85ed1dc62142fb594c5d34ccec747cf0121318828f4a0d0219b4c973
  （注意：上游 tag 名是 kup-0.10.0 无 v 前缀；任务卡原始 URL v0.10.0 为 404）

## 版本线抉择（关键决策）
1. kio 线：ohpcd 上 kio 6.18.0/6.26.0 均为 KIOCORE_ONLY 基线（KF6::KIOFileWidgets
   不交付，因为其 KF6 6.26 依赖 solid/kbookmarks/kcolorscheme/kjobwidgets/kiconthemes
   未全发布）；仅 kio/6.14.0 是完整构建（libKF6KIOCore/KIOGui/KIOWidgets/KIOFileWidgets
   四库实存）。kup 的 daemon/filedigger 链接 KF6::KIOFileWidgets → 必须钉 kio/6.14.0
   → 全图 KF6 6.14 线（ksystemlog 26.04.0 同款）。
2. kcmutils 仅发布 6.26.0 线 → 与 kio 6.14 冲突 → kcm/ 组件裁剪（连同其专属源码
   kcm/ 目录从根 CMakeLists 移除；kcm 是系统设置嵌入件，非核心功能）。
3. Plasma/Plasma5Support 不在档 → plasmoid-qt6 与 dataengine 裁剪（托盘小组件，
   daemon 的 QLocalSocket + DBus 通知通道保留，功能主体不受影响）。
4. Qt6::DBus：qtbase-sql-dbus/6.11.1 唯一提供者（libQt6DBus.so + Qt6DBus cmake
   配置实存；裸 qtbase/6.11.1 是 FEATURE_dbus=OFF 构建）。daemon 链接 Qt::DBus +
   KDBusService → 双 Qt 图混编（kglobalacceld 6.7.2 先例）：sql-dbus 前缀在
   conan_cmakedeps_paths.cmake 最后 PREPEND（查找顺序最前）。
5. libgit2/1.9.0：预构建二进制钉 openssl/1.1.1w + zlib/1.3.1，与 kio→karchive
   线（openssl/3.5.6 + zlib/1.3.1.1.1）硬冲突（conan graph info 实测报错）→
   配方 override openssl/3.5.6 + zlib/1.3.1.1.1 对齐，libgit2 package_id 随之
   变化，--build=missing 触发源码重建（v1.9.0 源走 gh-proxy 镜像可达）。链接
   target 是 libgit2::libgit2package（包自带 libgit2Config.cmake，CONFIG 模式），
   patch 0002/0003 将上游 LibGit2::LibGit2 改名。

## 交付物（裁剪后）
- bin/kup-daemon（备份调度守护进程）
- bin/kup-filedigger（bup 归档浏览器/恢复器）
- bin/kup-purger（旧备份清理器）
- lib/plugins/kf6/kio/kio_bup.so（bup 协议 KIO worker）
- hicolor 图标 + appdata + logging categories + notifyrc

## 构建要点
- QT_MAJOR_VERSION 钉 6（ohpcd 图仅 Qt6；上游靠 ECM 工具链推导）
- KF_IGNORE_PLATFORM_CHECK=TRUE；CMAKE_INSTALL_LIBDIR=lib；PLUGINDIR=lib/plugins
- lld: -Wl,-z,max-page-size=0x1000（musl loader 拒绝 0x10000 段分裂）
- SONAME flag 手工提供（CMake 无 Platform/HarmonyOS 模块）
- ECM_MODULE_PATH 手工注入 + conan_cmakedeps_paths.cmake 手工写
- RPATH: CMAKE_BUILD_RPATH/INSTALL_RPATH 注入全部依赖 lib 目录
- 构建期 LD_LIBRARY_PATH: 依赖 lib + SDK llvm/lib（lld 的 libxml2.so.16）+
  /system/lib64（libc++_shared.so 遮蔽修复）

## 测试
- 上游 0 用例（无 tests/ 目录）——如实申报
- test_package 冒烟 3 断言：filedigger/purger --version 输出 0.10.0；daemon 无
  kuprc 早退 "not enabled" 退出 0（KF6 运行时兼容层：签名刷新/软链农场/绝对
  NEEDED 修复，ksystemlog 26.04.0 先例）

## 错误台账（八轮 conan create，全部已修复）
| # | 首错 | 根因 | 修复 |
|---|---|---|---|
| 1 | CMakeLists.txt:16 找不到 ECMConfig.cmake | 上游 ECM-first 布局：find_package(ECM) 在 project() 之前，conan toolchain（含 conan_cmakedeps_paths.cmake include 钩子）要到 project() 调用才被处理，ECM 前缀不可见 | patch 0001：project(kup) 前移（纯重排） |
| 2 | ld.lld: undefined symbol KUiServerJobTracker::KUiServerJobTracker(QObject*) | kjobwidgets/6.14.0 为 USE_DBUS=OFF 构建，kuiserver 系列类被裁（libKF6JobWidgets.so 实测只导出 KWidgetJobTracker 系符号），头文件残留导致编译过链接炸 | patch 0004：KupDaemon::registerJob/unregisterJob no-op 化（Q_UNUSED），mJobTracker 成员与 include 移除；备份进度可见性由 KNotification 承担 |
| 3 | invalid preprocessing directive（kupdaemon.cpp 167-170） | 0004 补丁函数体内误用 C 风格 # 注释 | 重生成 0004 改 // |
| 4-6 | ratio:99/102/105 reference to unresolved using declaration intmax_t（kup-filedigger mocs_compilation.cpp 20 errors） | 误诊两轮（补 #include <cstdint>/-include cstdint 均无效）；真根因：libgit2 包 INTERFACE_INCLUDE_DIRECTORIES 导出 <pkg>/./include/git2，该目录内 libgit2 的 MSVC 兼容 stdint.h shim（全文包裹 #ifdef _MSC_VER，clang 下预处理为空）以 -I 优先级劫持 #include <stdint.h>，musl 真头从未被包含 → libc++『using ::intmax_t』落空；kup-daemon 不链 libgit2 全程编译通过（对照组） | patch 0001：get_target_property + set_target_properties 把 libgit2::libgit2package 的接口 include 目录由 /./include/git2 重指 /include（kup 以 <git2/global.h> 形式包含需父目录） |
| 7 | mergedvfs.cpp:14 fatal error: QDBusInterface file not found | filedigger 的 mergedvfs.cpp 用 QDBusInterface 调 daemon runIntegrityCheck，上游 Linux 靠 KF6::KIOCore 传递提供 Qt6::DBus 头，ohpcd kio/6.14.0 为 USE_DBUS=OFF 构建传递链断 | patch 0002：filedigger 显式补链 Qt::DBus（qtbase-sql-dbus/6.11.1 提供；daemon 目标同款写法已实证） |
| 8 | —（全绿） | — | conan create 成功；test_package 三断言全过 |

