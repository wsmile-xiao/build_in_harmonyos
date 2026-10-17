# kshisen 26.04.0 适配笔记

## Scope

KDE release-service 26.04.0 的 KShisen（Shisen-Sho 麻将接龙，QApplication
GUI 游戏，单可执行 `bin/kshisen`，无库产物）。官方发布归档：
`https://download.kde.org/stable/release-service/26.04.0/src/kshisen-26.04.0.tar.xz`
（SHA256 `a9ba5bed3520980bf70473d4183e57dcc990e71da60a050a63609b9ec4a457b4`，
任务书给定并已在本机复核一致）。

上游技术栈：CMake + ECM；Qt6 Core/Gui + KF6 十组件（CoreAddons/Config/
IconThemes/ConfigWidgets/Crash/DBusAddons/DocTools/I18n/WidgetsAddons/
XmlGui）+ KMahjongglib6 6.0.0 + KDEGames6 6.0.0；kconfig_add_kcfg_files +
ki18n_wrap_ui + qrc；icons/sounds 数据随包安装。

## Upstream tests: N=1（EVIDENCE_COMPLETE）

上游 26.04.0 恰好注册 1 个测试，已对照官方归档核证：

- `src/tests/CMakeLists.txt`：`add_executable(movetest movetest.cpp
  movetest.h ../move.cpp ../move.h)` + `add_test(NAME movetest COMMAND
  movetest)`，由 `BUILD_TESTING` 门控（`src/CMakeLists.txt` 尾部
  `if (BUILD_TESTING) add_subdirectory(tests)`）
- `movetest.cpp` 为 Qt Test（`QTEST_APPLESS_MAIN`，链接 `Qt6::Test`），
  15 个测试槽（x1/y1/x2/y2/tile1/tile2/hasSlide/slide/slideX1/slideY1/
  slideX2/slideY2/swapTiles + initTestCase/cleanupTestCase），约 37 个
  QCOMPARE 断言
- 全树 grep：唯一 add_test，N=1

真跑方式：`BUILD_TESTING=ON` + 配方 `build()` 内 `self.run(ctest
--output-on-failure --no-tests=error)`（keditbookmarks kbookmarkmodeltest
先例；sandbox HOME/XDG + offscreen QPA + `/system/lib64` 优先的
LD_LIBRARY_PATH）。`--no-tests=error` 把静默跳过变成硬失败，保证 N=1
真实进入统计。

## 关键决策

1. **KF6 6.14→6.18 override-UP**（任务书断点判定）：`conan cache path
   libkmahjongg/26.04.0` 读其配方，requires 钉死 6.14 线
   （kconfig/kconfigwidgets/kcoreaddons/kwidgetsaddons/ki18n 全 6.14.0）。
   若按 6.14 消费则与 libkdegames/26.04.0.1 的 6.18 二进制闭包混线（所有
   KF6 package id 变化、无 prebuilt binary）。方案：五个被钉框架全部
   `override=True` 提到 6.18.0（kjumpingcube kio/6.14.0 override-UP 先例：
   已安装 KF6 config 请求 find_dependency(KF6* >= 6.14)，6.18.0 满足；
   KF6 大版本内 ABI 稳定，已发布二进制干净链接）。
2. **libkdegames/26.04.0.1**（kjumpingcube 同款）：SONAME 修复版再发布；
   官方 26.04.0 是 SONAME 缺陷版，不可消费。
3. **kdoctools 裁剪**（knavalbattle/kgoldrunner 先例，双 patch）：
   ohpcd 无 kdoctools/6.18.0，其最新已发布二进制锚定 karchive/6.19.0，
   与本图 karchive/6.18.0 override 冲突。0001 从 KF6 umbrella 组件表移除
   DocTools + 注释 `kdoctools_install(po)`；0002 注释 doc/ 的
   `kdoctools_create_handbook`。另设
   `CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=TRUE`（kgoldrunner 先例）。
4. **qtbase-sql-dbus/6.11.1**（kjumpingcube 同款）：main.cpp 的
   KDBusService 需要 KF6DBusAddons → Qt6::DBus，只有该变体提供（E323/
   E441）；其 lib/cmake 在 conan_cmakedeps_paths.cmake 中确定性前置，
   防止 find_package(Qt6) 解析到传递带入的普通 qtbase 变体。该变体同时
   带 Qt6Test（movetest 链接）与 Core/Gui。
5. **karchive/6.18.0 override**：最新 kiconthemes/6.18.0 配方修订要求
   karchive/6.19.0，与 knewstuff/6.18.0 冲突（libkdegames/26.04.0.1
   同款解析）。
6. **openal-soft/libsndfile 显式 requires**：libKDEGames6.so 的
   DT_NEEDED（openal-soft 默认 static 会被 Conan 从消费者图剔除）。

## 配方要点

- package_type="application" + commands.json（type=tool, binary=false）
- ecm/6.26.0 tool_requires（ECM 模块对 6.18 KF6 线向后兼容）
- `KF_IGNORE_PLATFORM_CHECK=TRUE` + `KF_SKIP_PO_PROCESSING=ON`
- `-Wl,-z,max-page-size=0x1000`（OHOS lld 页布局 workaround）
- cmake_find_mode=none 的 qtbase/KF6 包：手工 conan_cmakedeps_paths.cmake
- 构建期宿主工具（kconfig_compiler_kf6/uic/rcc）LD_LIBRARY_PATH 注入 +
  `/system/lib64` 优先（OHOS libc++ shadow fix）
- package()：DT_NEEDED 就地 8 字节 d_val 重定向（path→basename）+
  llvm-objcopy 去 .codesign + binary-sign-tool 重签名（E537；patchelf
  禁用）
- test_package：path-form DT_NEEDED 闭环修复（real-file copy）+ cwd 相对
  解析基镜像 + offscreen 消费者冒烟 + libKDEGames6/libKMahjongg6
  DT_NEEDED 断言（test_kshisen.sh，L0c 独立测试源文件）

## 上游测试（N=1）

- movetest：15 槽 / ~37 QCOMPARE，ctest 真跑进 build log
- 消费者测试补偿：test_package 四断言（--version 冒烟 + 无 path-form
  DT_NEEDED + libKDEGames6 + libKMahjongg6 在 NEEDED）
