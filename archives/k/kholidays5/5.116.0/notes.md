# kholidays5 5.116.0 适配笔记

## 编译环境
- 构建系统: cmake (Makefiles, CMAKE_BUILD_PARALLEL_LEVEL=1)
- 编译日期: 2026-10-06
- 编译器: clang / clang++（HarmonyOS PC 工具链，aarch64，libc++，--target=aarch64-linux-ohos）
- 状态: built（conan create 全绿，上游 5 autotests + test_package 通过，未 upload）

## 命名说明

上游项目实名 kholidays（Tier 1 Frameworks）。官方 5.116.0 tarball 为
`kholidays-5.116.0.tar.xz`（download.kde.org 对 KF5 终版线发 302 跳转到 Attic 存档区，
conan get() 跟随即可；curl -L 实测 200，256892 字节）。本配方包名 kholidays5（平台任务
#14898 登记），与 KF6 线 kholidays/6.28.0（libKF6Holidays.so、qtbase/6.11.1 链）为
不同包名不同 Qt 线，无冲突。sha256 双源实测（官方 302 链 + ftp.gwdg.de Attic 镜像）
一致：898fa19e4dbd089a4b00693b8226982f5cbb1751cf4fa21565eb93141b15fdc0。
清华/中科大镜像对 Attic 路径 404（未同步 5.116 终版），conandata 仅写官方单条 URL（R39）。

## 上游结构（kholidays-5.116.0.tar.xz）

| 目标 | 内容 |
|------|------|
| KF5Holidays | 核心库 libKF5Holidays.so（SOVERSION 5，命名空间 KHolidays）：HolidayRegion/Holiday（153 区域假日数据经 holidays.qrc 内嵌 + plan2 手写解析器）、LunarPhase、Zodiac、AstroSeasons、SunRiseSet。链接仅 Qt5::Core |
| kholidaysdeclarativeplugin | QML 插件 org.kde.kholidays 1.0（HolidayRegionsModel + Lunar/SunRiseSet gadget 单例），链接 Qt5::Qml/Core，ecm_add_qml_module 安装到 <lib>/qml/org/kde/kholidays |

顶层 REQUIRED：ECM 5.116.0（ecm/6.26.0 满足，kcoreaddons5 同法）+ Qt5 5.15.2 Core/Qml。
无任何 KF5 库依赖（Tier 1）。autotests 另需 Qt5Test。

## 关键适配点

### 1. Qt5 双包供给（kpeople5 先例缩减版）
顶层 `find_package(Qt5 5.15.2 CONFIG REQUIRED Core Qml)` 需一个聚合 config 同时供给两个包的组件：
- qt5-qtbase/5.15.2.2：Core/Network/Gui/Test（原生 per-module config，cmake_find_mode=none）
- qt5-qtdeclarative/5.15.2：Qt5Qml（CMakeDeps cmake_file_name=Qt5Qml，仅库无 config）

手写聚合 `Qt5Config.cmake` shim 放 generators 目录（CMAKE_PREFIX_PATH 最前，精确名匹配
优先于小写 qt5-config.cmake 聚合）。shim 先置 `Qt5_FOUND TRUE` 防 Qt5QmlConfig 的
find_dependency(Qt5) 重入。

### 2. 预生成解析器（与 KF6 线差异）
5.116.0 tarball 内 src/parsers/plan2/ 已含预生成的 holidayparserplan.cpp / holidayscannerplan.cpp
（与 .ypp/.lpp 语法文件同装），无需 bison/flex/m4 tool_requires——KF6 kholidays/6.28.0
tarball 已删预生成文件需 bison/3.8.2 + flex/2.6.4 + m4/1.4.19，本 5 线不需要。

### 3. QML 插件（ECMQmlModule5）
QT_MAJOR_VERSION=5 时 ECMQmlModule 走 ECMQmlModule5.cmake（Qt5 实现）：ecm_add_qml_module
仅设 target 属性，ecm_finalize_qml_module 生成 qmldir 并 install(TARGETS) 到
KDE_INSTALL_QMLDIR（默认 lib/qml）。无 qmlplugindump/qmlimportscanner 调用（无 QML 源
文件，纯 C++ 插件 + .moc）。AUTOMOC_MOC_OPTIONS -Muri=org.kde.kholidays 由 ECM 注入。

### 4. poqm 处理
KF_SKIP_PO_PROCESSING=ON 跳过 poqm/ → .qm 目录处理（ecm_process_po_files_as_qm/
ecm_install_po_files_as_qm 提前 return）；ecm_create_qm_loader 仍生成 qm loader 源文件
链入库（空目录集），库 API 完整（链级约定，Qt5LinguistTools 未发布到 ohpcd）。

### 5. 上游测试（BUILD_TESTING=ON，ctest 真跑）
| 测试 | 形态 | 函数数 |
|------|------|--------|
| testlunar | QTEST_MAIN(LunarTest) | 3（test2005/test2007/testIntermediatePhases） |
| testseasons | QTEST_MAIN(SeasonsTest) | 2（test_data/test，QFETCH 数据驱动多行） |
| testsunriseset | QTEST_MAIN(SunriseTest) | 5（TestSunrise/TestSunset/TestDawn/TestDusk/TestPolarDayNight） |
| testzodiac | 纯 main() 冒烟（无断言，遍历 2004 全年双 zodiac 打印） | 1（ctest 1 条） |
| testholidayregion | QTEST_MAIN(HolidayRegionTest) | 11 Q_SLOTS（testLoadFileCalendarSystems/testLoadFile/testGb/testIran/testIsrael/testRegions/testDefaultRegions/testSolistaleInHolidays/testLoadFileCalendarSystemsForPlasma/testDominicanRepublicDiadelaConstitucion/testUsAmericanJuneteenth） |

- 纯计算测试：假日/天文数据内嵌库中（holidays.qrc），无显示/无会话服务/无插件扫描
- testholidayregion 的三个 fixture（holiday_calendar_systems、holiday_gb-eaw_en-gb_Test、
  holiday_solstice_in_holidays）经 KDESRCDIR（编译期 -D 注入源码目录）解析，tarball 内齐全
- TZ=UTC + QT_QPA_PLATFORM=offscreen；ctest 运行时库经 <build>/../bin 兼容链接目录解析
  （相对 soname ../bin/libKF5Holidays.so，OHOS 剥离 install rpath，kconfig/kcalcore 先例）
- testzodiac 无 QVERIFY 断言（纯打印），ctest 以退出码 0 判过——上游形态如此，如实统计

### 6. ELF 签名
package() 对包内所有 ELF（libKF5Holidays.so + qml 插件）binary-sign-tool 自签
（llvm-objcopy 先清 .codesign 段）；kcalcore/libical 先例。

## 交付物
- lib/libKF5Holidays.so（未版本化 DT_SONAME，W3 L5）
- lib/qml/org/kde/kholidays/（插件 + qmldir）
- lib/cmake/KF5Holidays/（KF5HolidaysConfig.cmake + Targets + Version）
- include/KF5/KHolidays/、share/（logging categories）、mkspecs（.pri）
