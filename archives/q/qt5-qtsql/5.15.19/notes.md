# qt5-qtsql 5.15.19 供给包笔记

## 任务背景
- librepcb 1.2.0（contrib-242）需要 Qt5::Sql——仓内全量排查无供给：
  qt5-qtbase/5.15.2 无 Sql、qt5-qtbase/5.15.2.2 显式 -no-feature-sql、
  qt5/5.15.19 缺 Sql/LinguistTools、qt-unixodbc/5.15.2 只有 libQt5Sql.so
  无头文件无 CMake config（find_package 编译期不可用）
- 本包为独立 Sql 供给：同源 qtbase 5.15.19 单编 src/sql + qsqlite 插件

## 打包四件套（qt-unixodbc 只带 .so 的坑不重蹈）
1. lib/libQt5Sql.so（含 .so.5/.so.5.15/.so.5.15.19 符号链全链）
2. include/QtSql（完整头）+ include/QtCore 公共宏头
3. lib/cmake/Qt5Sql（CMake config——find_package(Qt5 COMPONENTS Sql) 可用）
4. plugins/sqldrivers/libqsqlite.so（缺插件运行期报 QSQLITE driver not loaded）

## 关键坑（16 轮实证）

1. **QT_PLUGIN_PATH 语义**：须指向 **plugins 根目录**（Qt 自拼 sqldrivers
   子路径）——指向 sqldrivers 子目录则 QFactoryLoader 静默找不到驱动
   （available drivers 空列表）。cwd 相对插件扫描叠加时症状更隐蔽。
2. **qt in-source 构建布局**：qmake 产物在 source_folder 根（b/lib、
   b/plugins、b/include），非 build 子目录——package() 拷贝源用
   self.source_folder。
3. **package_info 组件 requires 须引用全部直接依赖**（zlib 漏声明报
   "direct dependency not used by any components"）。
4. **CMakeDeps target 名**：全局 target 是 qt5-qtsql::qt5-qtsql（非
   组件路径名 Qt5::Sql）——consumer 的 CMakeLists 用包名前缀 target。
5. **QCoreApplication 依赖**：Qt 插件加载需应用实例先建
   （QSqlDatabase::addDatabase 前须 QCoreApplication app(argc, argv)）。

## ABI 一致性
- 与 qt5/5.15.19 主包同源码同 configure 框架（唯一差异 -sql-sqlite），
  同 profile 构建——libQt5Sql 链主包 libQt5Core 无版本冲突。

## 验证
- conan create 完整流水线全绿（第 16 轮）
- test_package：QSQLITE :memory: 建表/插入/读回 roundtrip PASS
  （运行环境：LD_LIBRARY_PATH 双包 lib + QT_PLUGIN_PATH=plugins 根）
