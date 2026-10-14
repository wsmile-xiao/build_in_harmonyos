# kpeople5 5.116.0 适配笔记

## 编译环境
- 构建系统: cmake (Ninja)
- 编译日期: 2026-10-01
- 编译器: clang / clang++（HarmonyOS PC 工具链，aarch64，libc++）
- 状态: built（conan create 通过，W3 本地验证通过，未 upload）

## 上游结构（v5.116.0 tarball）

四个库目标：
| 目标 | 内容 |
|------|------|
| KF5People | 核心库：PersonData / PersonsModel / PersonPluginManager / PersonsSortFilterProxyModel / PersonManager(sqlite) |
| KF5PeopleWidgets | widgets 增件：PersonDetailsView / MergeDialog / actions 等（ki18n_wrap_ui 处理 .ui） |
| KF5PeopleBackend | 数据源插件 API：AbstractContact / BasePersonsDataSource / AllContactsMonitor 等 |
| KF5PeopleDeclarative | QML 插件，安装到 <lib>/qml/org/kde/people |

顶层 REQUIRED：Qt5 Gui/Sql/Widgets/Qml/Quick + KF5 CoreAddons/WidgetsAddons/I18n/ItemViews @5.116.0。
Qt5DBus 为 OPTIONAL 分支（OHOS 强制 CMAKE_SYSTEM_NAME=Linux 后走 `UNIX AND NOT APPLE` 的 REQUIRED 分支——qt5-qtbase/5.15.2.2 提供 Qt5DBus 满足之）。

## 三源 Qt5 接线（本包核心适配点）

KF5 链此前只需单一 qt5-qtbase；kpeople5 顶层 find_package 一次要六个组件，需三包协同：

| 组件 | 供给包 | 消费方式 |
|------|--------|----------|
| Core/Gui/Widgets/Test/DBus | qt5-qtbase/5.15.2.2 | 原生 config（cmake_find_mode=none + CMAKE_PREFIX_PATH） |
| Sql | qt5-qtsql/5.15.19 | 原生 config（cmake_find_mode=none + CMAKE_PREFIX_PATH） |
| Qml/Quick | qt5-qtdeclarative/5.15.2 | CMakeDeps 生成（cmake_file_name=Qt5Qml，仅 libQt5Qml/Quick 无 config） |

### 坑 1：qt5/5.15.19 小写 config 劫持聚合 find_package
qt5-qtsql 传递 requires qt5/5.15.19 主包，CMakeDeps 为其生成小写 qt5-config.cmake
（组件仅 Core/Network/Gui/Widgets/Test/Xml/Concurrent，无 Sql/Qml/Quick）。CMake 对
`find_package(Qt5 CONFIG)` 的大小写不敏感匹配会命中它 → 组件缺失直接失败。
**解法**：① qt5 也设 `cmake_find_mode=none`（生成器目录里不再出现 qt5-config）；② 手写聚合
`Qt5Config.cmake` shim 放 generators 目录（该目录已在 CMAKE_PREFIX_PATH 最前，精确名匹配
优先），shim 内 find_dependency 各原生 per-module config + CMakeDeps 的 Qt5QmlConfig，
并定义 INTERFACE `Qt5::Quick` 转发 target（qtdecl 包把 Quick 库暴露在 Qt5Qml 全局组件里，
无独立 config）。

### 坑 2：kcoreaddons5 钉死 qt5-qtbase/5.15.2 引起版本冲突
kcoreaddons5/5.116.0（已发布）requires qt5-qtbase/5.15.2，与 KF5 链 5.15.2.2 混图被 conan
拒绝。**解法**：`self.requires("qt5-qtbase/5.15.2.2", force=True)` 整图归一到 DBus 超集
二进制（5.15.2.2 ⊇ 5.15.2 ABI 兼容）。

### 坑 3：qtdecl 的 Qt5QmlConfig 反向 find_dependency(Qt5)
探针实测 qt5-qtdeclarative 的 CMakeDeps data 里 `FIND_DEPENDENCY_NAMES` 含 `Qt5`（其
requires qt5-qtbase→cmake_file_name 无 → 生成 Qt5 名）。shim 先于 Qt5QmlConfig 被载入
（聚合 find_package 先行），Qt5_FOUND 已置 TRUE，cmakedeps 的 find_dependency 有
`if(NOT Qt5_FOUND)` 守卫，不会重入死循环。

### 坑 4：Qt5Sql 依赖 Core 5.15.19 版本串
qt5-qtsql 原生 Qt5SqlConfig 的依赖循环 `find_package(Qt5Core 5.15.19 PATHS
${CMAKE_CURRENT_LIST_DIR}/.. NO_DEFAULT_PATH)` 限定在 qtsql 包自己的 lib/cmake 下找
Qt5Core——该目录只有 Qt5Sql/，找不到就静默 return FALSE？实测 qtsql 包 lib/cmake/Qt5/ 有
Qt5Config.cmake（Qt5ModuleLocation 机制），但无 Qt5Core 目录。shim 里 **先** find_dependency
qtbase 的 Qt5Core（5.15.2 满足 ≥5.15.19？否——5.15.2 < 5.15.19！）
→ **此处待 conan create 实测定**：若 Qt5Sql 因 Core 版本 5.15.2 < 5.15.19 失败，则调序：
先 find Qt5Sql 再让其在 qtsql 包内解析（或设 Qt5Core_DIR 指向 qtbase 的 config）。librepcb
先例（qt5/5.15.19 主包 + qtsql 同线）无此问题，因为它整条线都是 5.15.19。

## CMake 开关（全部经 toolchain 变量）

- QT_MAJOR_VERSION=5、KF_IGNORE_PLATFORM_CHECK=TRUE、KF_SKIP_PO_PROCESSING=ON
- KDE_INSTALL_USE_QT_SYS_PATHS=OFF、BUILD_TESTING=ON、BUILD_QCH=OFF、BUILD_SHARED_LIBS=ON
- ENABLE_EXAMPLES=OFF（examples/ 是 GUI demo app，非交付物）
- CMAKE_SYSTEM_NAME=Linux（OHOS→HarmonyOS 无 UNIX/平台模块；ECM ctest 注册需要非交叉态）
- CMAKE_BUILD_PARALLEL_LEVEL=1（HMDFS 拒绝 make jobserver fifo）
- CMAKE_BUILD_WITH_INSTALL_RPATH=ON（E537：安装期不改写 ELF）
- CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE + SONAME_FLAG（L5 门禁：无版本 DT_SONAME）
- CMAKE_AUTOMOC/AUTORCC/AUTOUIC_EXECUTABLE → qt5-qtbase bin/ 工具
- mkspec 兼容复制（<pkg>/../b/mkspecs 树重建，kcoreaddons5 先例）
- ECM_DIR / ECM_MODULE_PATH 手工接线（ecm 是 tool_requires）

## 上游测试（R51）

清点（tarball 实测）：autotests/ 注册 **3 个** ecm_add_test QTEST 目标：
| 目标 | 测试函数 |
|------|----------|
| persondatatest | loadContact / loadPerson / contactChanged / nullPerson / removeContact（5） |
| personsmodeltest | loadModel / mergeContacts / gettersTests / unmergeContacts（4） |
| personsproxymodeltest | testFiltering（1） |

合计 **10 个测试函数**（rule4 口径：上游构建系统注册的测试目标 3 个，变体不折叠）。
三个都是 QTEST_GUILESS_MAIN + FakeContactSource 桩（setDataSourcePlugins 注入，无插件扫描）
+ QTemporaryFile sqlite DB（无 QStandardPaths 数据目录依赖）+ PersonManager merge 操作。
**无 D-Bus session 依赖**（PersonManager 的 dbus 通知在 QT_DBUS_LIB 未定义时编译掉；
测试链无 sessionBus 调用）→ OHOS 沙箱可真跑全量。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| qt5-qtbase | 5.15.2.2 | force=True 归一（kcoreaddons5 钉 5.15.2 的冲突解法） |
| qt5-qtdeclarative | 5.15.2 | Qt5Qml/Qt5Quick 供给 |
| qt5-qtsql | 5.15.19 | Qt5Sql + QSQLITE 驱动 |
| kcoreaddons5 / kwidgetsaddons5 / ki18n5 / kitemviews5 | 5.116.0 | KF5 依赖 |
| ecm | 6.26.0 | build-only（tool_requires） |

## 验证结果

（conan create 后回填）

## 注意事项

- 纯库包（KF5People/KF5PeopleWidgets/KF5PeopleBackend/QML 插件），无 commands.json（R38）。
- QML 插件 KF5PeopleDeclarative 安装在 lib/qml/org/kde/people（KDE_INSTALL_QMLDIR），
  供 QML 引擎 import org.kde.people 用。
- PersonManager 单例惰性建 sqlite（测试传 QTemporaryFile 路径；生产走
  QStandardPaths::GenericDataLocation + /kpeople/persondb）。

## 编译结束

（收尾后回填最终状态）
