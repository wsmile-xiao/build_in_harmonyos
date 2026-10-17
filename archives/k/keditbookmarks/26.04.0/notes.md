# keditbookmarks 26.04.0 适配笔记

## 概要
KDE 书签编辑器（KDE Gear 26.04.0 应用件）。交付两个可执行文件
（keditbookmarks GUI + kbookmarkmerger CLI）与一个私有共享库
libkbookmarkmodel.so。

## 编译环境
- 构建系统: cmake (ECM/KDEInstallDirs)
- 编译日期: 2026-09-19
- 编译器: clang/clang++（OHOS aarch64 profile，cppstd 17）
- 状态: built

## 版本链选择（关键决策）
1. **KF6 6.14.0 基线**：kio/kxmlgui/kbookmarks/ktextwidgets 只有 6.14.0
   与 6.18.0/6.26.0 两批已发布二进制；6.14.0 批全部与 qtbase/6.11.1
   （无 DBus）一致，graph 全量复用已发布二进制，无需 override、无需
   从源码重编任何依赖。已实证：kio/kxmlgui/kbookmarks/ktextwidgets/
   kcodecs/kcompletion/kconfigwidgets/kconfig/kcoreaddons/ki18n/
   kiconthemes/kitemviews/kwidgetsaddons/kwindowsystem/kcrash/
   kservice/solid/kauth/karchive/kcolorscheme/kguiaddons/kjobwidgets
   6.14.0 全部在制品仓可下载；sonnet 由 ktextwidgets 引 6.26.0
   （版本范围 [6.14.0,7.0) 接受，ktextwidgets 自己的声明）。
2. **ecm/6.20.0**（tool_requires）：kio 6.14.0 同款（6.18.0 不在仓）。
3. **kdoctools 不引入**：上游 TYPE OPTIONAL，制品仓只有 6.19.0（与
   6.14 基线版本冲突，kfourinline 同款卡点）。不装即自动跳过 doc/。
4. **kparts 剔除**（patch 0001）：制品仓无任何版本（6.14/6.18/6.26
   实证 conan install 全部 not resolved），且其唯一用途
   （FavIconUpdater::downloadIconUsingWebBrowser + FavIconWebGrabber）
   运行时加载 text/html KPart——OHOS 无 HTML part，本来就是死路径。
5. **Qt6 DBus 剔除**（patch 0001）：qtbase/6.11.1 无 DBus（6.11.1.1
   才有）。DBus 使用仅两处且在 OHOS 上均为运行时空转：main.cpp askUser()
   枚举 session bus 检测另一实例（无 session bus 时 reply 无效直接
   return true）；toplevel.cpp registerObject（无 bus 时静默失败）。
   选择剔除而非 override qtbase/6.11.1.1：override 会使 kio 6.14 等
   全链包 id 改变触发源码重编（R36 大坑）。

## 补丁（patches/0001-ohos-adaptation.patch）
- CMakeLists.txt: Qt6 REQUIRED COMPONENTS Core DBus→Core；KF6 列表去
  Parts。
- src/CMakeLists.txt: 删 qt_generate_dbus_interface/qt_add_dbus_interface
  （toplevel_interface 生成代码）；keditbookmarks 链接去 KF6::Parts、
  Qt6::DBus。
- src/faviconupdater.h/.cpp: 删 FavIconWebGrabber 类与
  downloadIconUsingWebBrowser/setIconUrl（KParts 死路径）；保留
  KIO::favIconForUrl + KIO::FavIconRequestJob 主路径，失败直接
  done(false, errorString)。
- src/main.cpp: 删 askUser()（DBus 单实例检测）；KEBApp 构造 readonly
  固定 false。
- src/toplevel.cpp: 删 QDBusConnection registerObject。

## 关键配方手法（baloo 26.04.3 / libkdegames 26.04.0 先例）
- ECM_MODULE_PATH 手动指 ecm/6.20.0 share/ECM/{modules,find-modules,
  kde-modules}（CMakeDeps 生成的 ECMConfig 不传播该变量）。
- generate() 手写 conan_cmakedeps_paths.cmake：全部依赖 lib/cmake +
  lib + include 前插（qtbase/KF6 包均 cmake_find_mode=none）。
- _build_env：LD_LIBRARY_PATH=各依赖 lib + build bin/lib + /system/lib64
  追加（host 工具 moc/kconfig_compiler_kf6 需要）；libxml2/2.15.3 lib
  前插（OHOS SDK lld 链接期需要 libxml2.so.16，kio 先例）。
- CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG=-Wl,-soname,（无 HarmonyOS
  平台模块时显式给 soname，baloo 先例）。
- KF_SKIP_PO_PROCESSING=ON 跳过 po 目录处理（无 lconvert）。
- 上游测试：BUILD_TESTING=ON，ctest 跑 kbookmarkmodeltest（上游注册
  唯一测试目标），offscreen + 沙箱 HOME/XDG。
- _prepare_test_runtime_links：已发布 KF6 二进制 DT_NEEDED 含构建树
  相对路径（../../bin/libKF6*.so），musl 按 CWD 解析——在
  ../bin 建依赖 .so 软链接农场（ktextwidgets/kxmlgui 先例）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|---------|
| 1 | kparts 制品仓全版本缺失 | 平台从未适配 | patch 剔除（使用点为 OHOS 死路径） |
| 2 | Qt6::DBus 未发布 | qtbase/6.11.1 FEATURE_dbus=OFF | patch 剔除（单实例检测+对象注册两处运行时空转）；不用 6.11.1.1 override 以免全链重编 |
| 3 | kdoctools 6.19.0 与 6.14 基线冲突 | 版本链断裂 | 不引入（上游 OPTIONAL 自动跳过 doc/） |
| 4 | 任务描述上游 URL pim/keditbookmarks 404 | 上游已迁 utilities/ | 用官方 release tarball（download.kde.org）+ homepage 指 utilities |

## 上游测试
- 上游注册测试数 N=1（kbookmarkmodeltest，QTest；BUILD_TESTING 才注册）
- 本机 conan create 内 ctest 执行：**1/1 PASS**

| # | 问题 | 根因 | 解决方案 |
|---|------|------|---------|
| 5 | 已发布 KF6 二进制 RPATH 指向 ~/.cache/conan2（CI home），本机是 ~/.conan2 | 发布 worker 与本机 conan home 不同 | ~/.cache/conan2/p/ 下补同名软链（仅本机验证环境；CI 一致无需处理，ktextwidgets notes 同款） |
| 6 | 测试进程 Error loading ../../bin/libKF6*.so | 已发布 KF6 包 DT_NEEDED 含构建树相对路径，musl 按 CWD 解析 | _prepare_test_runtime_links：build 树各层 bin/ 建依赖 .so 软链农场 |
| 7 | kbookmarkmodel 链接失败 KF6::XmlGui not found | 顶层 find_package(KF6) 组件列表无 XmlGui（上游假设传递）；CMakeDeps 模式不传递 | patch 顶层 CMakeLists 显式加 XmlGui 组件 |
| 8 | faviconupdater.cpp 编译错 favIconForUrl/FavIconRequestJob 未声明 | 重写时丢了 KIO 头 | 补 #include <KIO/FavIconRequestJob> + <KIO/Global> |
| 9 | main.cpp 编译错 QDir 未声明 | 原 include 链经删除的 toplevel_interface.h 传递引入 QDir | 补 #include <QDir> |
| 10 | test_package --exportns 挂死 | KNSBookmarkExporterImpl::write 目标文件不存在时弹 QMessageBox::critical（offscreen 下模态永久阻塞） | 预创建空输出文件（上游 rename 成 .beforekde 后正常写出） |

## test_package 冒烟（bin 交付验证）
1. kbookmarkmerger --help → usage 文本 + exit 0 ✅
2. keditbookmarks --importkde3 bookmarks.xml → exit 0（默认 XBEL 库写入）✅
3. keditbookmarks --exportns out.html → exit 0，输出 Netscape HTML 含导入的两条书签 ✅
（上游规则：每次调用只能带一个 --import*/--export* 选项，故分两步）
---

**编译结束**: 2026-09-19 12:44
**最终状态**: built
