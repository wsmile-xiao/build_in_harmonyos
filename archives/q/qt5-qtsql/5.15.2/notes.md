# QtSql 5.15.2 鸿蒙适配记录

## 目的和范围

KPeople 5.116.0 需要 Qt5Sql。已发布的 qt5-qtbase/5.15.2.2 关闭了 SQL；本包仅补充同版 QtSql 共享库、公开/私有头文件和 QSQLITE 插件，不重复打包 QtCore。

源码使用官方 QtBase 5.15.2 发布包，与 qt5-qtbase/5.15.2.2 的上游版本和摘要完全相同。现有 qt5-qtsql/5.15.19 服务于另一套 qt5/5.15.19，本次保留其原配方和元数据。

## 构建

- 原生 clang，调用上游 src/sql/sql.pro 和 src/plugins/sqldrivers/sqlite/sqlite.pro，make -j1。
- 依赖 qt5-qtbase/5.15.2.2、sqlite3/3.53.4，两者已实际下载对应鸿蒙二进制。
- 复用已发布 QtCore 和生成工具，不重编整个 QtBase。
- SQLite 使用 Conan 包的静态库；不编译 Qt 源码内嵌 SQLite。
- 在独立构建目录复制 mkspecs，使用 modules-inst 元数据重定位路径；不改共享依赖缓存。
- 明确 QT_TOOL.moc.binary，避免 qtPrepareTool 将 QMAKE_MOC 覆盖为发布者旧构建路径。
- 为复制后的 qt_functions.prf 添加 HarmonyOS/OHOS 的 LD_LIBRARY_PATH 分支，支持测试构建工具运行；无平台宏注入。
- 保留 src/sql 的影子构建目录层级，使 qmake shadowed() 正确计算输出路径。
- 根据上游 configure.json 和已启用的 QtCore itemmodel，生成 sqlmodel 配置。
- 不执行会写入依赖包前缀的 make install；仅收集本包产物及真实头文件，避免转发头引用源码树。

## 上游测试

清点 tests/auto/sql，13 个测试程序全部参与构建和运行。探索验证结果：252 passed、0 failed、86 skipped。计数含 QtTest 生命周期项，不等同于业务方法数或断言调用数。

跳过项是上游根据数据库驱动和能力条件自行判定，主要涉及 MySQL、PostgreSQL、Oracle、ODBC 等未提供的驱动及其专属行为；未用消费者冒充上游测试。

首次原样运行时，tst_qsqlquery 的 sqliteVirtualTable 因已发布 SQLite 未启用 FTS3 而失败。SQLite 包启用了 FTS5，补丁读取 PRAGMA compile_options 选择可用 FTS3/FTS5，保留全部原有预处理、错误查询、插入、读取和 MATCH 断言。两种引擎均不可用时仍失败，不把该用例无条件跳过。

## 消费者验证

消费者仅直接声明被测包，通过 CMake 的 Qt5::Sql 目标编译链接，检查：

- QSQLITE 插件可用及数据库打开。
- 中文和 BLOB 参数绑定、插入与查询。
- 事务提交、删除和回滚。
- QSqlTableModel 数据加载。
- 数据库关闭并重新打开后的持久化。

正式 conan-verify 已通过：13 个上游测试程序执行成功，独立 CMake 消费者的 19 个业务检查通过。尚未发布到远端制品仓。

## 已知限制

当前供给 SQLite 驱动；不提供依赖外部服务的其他 SQL 驱动。匹配同版 Release QtBase 的原生构建，不承诺跨主机运行目标平台 qmake/moc。

下一步：conan-verify → finish 干净构建门禁 → 独立审计 → 独立 PR/CI → 发布后继续 KPeople。
## 收尾工具诊断

通用 G0 固定执行整个源码根目录 configure，无法表达本包仅构建 QtSql 的 qmake 流程，因此该项失败；完整配方由 conan create 和 W3 实测验证，不宣称通用 G0 通过。首次 W3 未提交分支回退全仓扫描，被主仓库其他包已跟踪的 5 个历史状态文件阻断；使用检查器支持的 JUNK_PR_DIFF 指向本包实际暂存差异，保持检查规则不变。
---

**编译结束**: 2026-10-01 22:42
**最终状态**: built

## 本地 CI 验证

W3 原生重建通过，13 个上游程序和消费者验证通过，破坏性反向测试确认真实依赖。详见 reports/test-report.md。整体 finish 仍受主仓库存量知识字段和 SUMMARY 解析异常影响，不能宣称所有收尾步骤无误。R19 已废弃手工 packaging，本包遵守 Conan 产物流程。
