# E666（草稿）：Qt5 线二进制 ABI 互斥的供给线选择与 QSQLITE 插件配方内自编（含 HMDFS 挂载路径消费者视角注入）

> 实证：kpeople5 5.116.0 适配（PR #14576，j669539）。
> 编号说明：原取 E551，origin/main knowledge/drafts/ 上 E551 已被多份草稿占用
> （DRAFT-E551-ohos-conan-configshell-bash-libtool-escaping、E551-draft-A7F3/CCD4、
> E551-draft-J669 fingerterm 等），按"被占顺延"取首个空位 E666（E551-E664 均占，
> E666 空闲）。最终编号由主编确认。

## 错误特征（出现任一即在本文档射程内）

- 运行期 abort：`Cannot mix incompatible Qt library`（qt_version_tag 比对失败）
- `QSqlDatabase: QSQLITE driver not available` / `available drivers:` 里没有 QSQLITE
- 插件 dlopen 失败：`Error relocating QSqlDriver::notification(QString): symbol not found`
- `/proc/self/maps` 报出的库路径 `fopen` 失败（`/data/service/el2/...` HMDFS 内核侧路径，Permission denied）
- cmake 层：`find_package(Qt5 COMPONENTS Sql)` 命中错误供给包的小写聚合 config，报组件缺失

## 根因

1. **Qt5 线二进制 ABI 互斥**：Qt 各 .so 链接期把 `qt_version_tag` 符号按构建时的
   Qt 补丁行烧进 ELF；QLibrary 加载器逐符号比对。ohpcd 仓 qt5-qtbase 主线是
   5.15.2.2，qt5-qtsql 主线是 5.15.19——KF5 全链（已发布的 kcoreaddons5 等全部
   requires qt5-qtbase/5.15.2.2）在二进制层面无法消费 qt5-qtsql/5.15.19 的
   libQt5Sql 与其 QSQLITE 插件。这是 ELF 符号级边界，cmake 版本约束解不了。
2. **5.15.2 线有库无驱动**：KPeople PersonManager 把 persons 数据库存进 sqlite
   （`QSqlDatabase::addDatabase("QSQLITE")`），5.15.2 线仓库只有 qt-unixodbc 提供
   libQt5Sql（其配方本身就用"官方 qtbase-everywhere-src-5.15.2 tarball + 手动
   clang+moc"自编 ODBC 插件）——Sql 库存在，SQLITE 驱动插件不存在。
3. **HMDFS 路径差异新形态**：挂载路径在进程沙箱内不可 fopen（/proc/self/maps 报
   内核侧 `/data/service/el2/...` 路径）。区别于已收录条目（E011/E052 只读与
   临时目录权限、E050/E073 符号链接、E079 硬链接）：本条是"路径查询通道本身给出
   不可开路径"——maps 的内核侧视角 ≠ 消费者视角（conan 包路径）。

## 解法（kpeople5 5.116.0 实证，三段组合）

### ① 供给线选择：qt-unixodbc/5.15.2 线 Qt5Sql

```python
self.requires("qt-unixodbc/5.15.2")   # 5.15.2 线 libQt5Sql，qt_version_tag 与 5.15.2 线 libQt5Core 匹配
# qt-unixodbc 不带 cmake config 与头文件：
deps.set_property("qt-unixodbc", "cmake_find_mode", "none")
# 手写 Qt5SqlConfig.cmake：IMPORTED UNKNOWN 指向其 lib/libQt5Sql.so，
# 头文件走 qt5-qtbase/5.15.2.2 的 include 与 include/QtSql；
# 并暂存 qtbase src/sql/qtsql-config.h 到 <generators>/QtSql/
#（打包的 QtSql 公共头会 include <QtSql/qtsql-config.h>，它在 include/QtSql 之外）
```

### ② QSQLITE 插件配方内自编（qt-unixodbc 同款手法）

- conandata 挂官方 `qtbase-everywhere-src-5.15.2.tar.xz`，sources() 期下载解包；
- `_build_qsqlite_plugin()`：qtbase bin/moc 预跑 qsql_sqlite.h → moc_qsql_sqlite.cpp；
  sqlite3.c（qt 自带 3rdparty）与 qsql_sqlite.cpp/smain.cpp 各自 -c；
- **`-DQT_DISABLE_DEPRECATED_BEFORE=0x050F00` 把 1 参 notification() 编译掉**——
  5.15.2 线 libQt5Sql 未导出该重载，不剪则 dlopen 报
  `Error relocating QSqlDriver::notification(QString): symbol not found`；
  3 参重载保留，通知能力不损失；
- `cxx -shared -o libqsqlite.so ... -lQt5Sql -lQt5Core -Wl,-soname,libqsqlite.so`；
- **双布局落盘**：`<build>/bin/sqldrivers`（Qt 恒扫应用目录）+
  `<build>/qsqlite-stage/plugins/sqldrivers`（QT_PLUGIN_PATH 条目）。ECMAddTests
  会在 configure 期把 QT_PLUGIN_PATH 冻进 ctest ENVIRONMENT 属性并覆盖运行期
  env——两处都必须放，缺一 ctest 找不到驱动。

### ③ KPEOPLE_SO_PATH 消费者视角路径注入

```cmake
# test_package/CMakeLists.txt：configure 期从 imported target 取真实包路径
target_compile_definitions(test_kpeople5 PRIVATE
    KPEOPLE_SO_PATH="$<TARGET_FILE:KF5::People>")
```
```cpp
// test.cpp：优先消费者视角宏，仅空时回退 /proc/self/maps
std::string so_path = KPEOPLE_SO_PATH;
if (so_path.empty()) { so_path = loaded_library_path("libKF5People.so"); }
```

## 降级方案

- 供给线：整链统一切 qt5-qtsql/5.15.19 线（对已发布 KF5 链通常不可行）；或静态
  链接 Qt5Sql 规避运行期比对。
- 插件：qtbase tarball 不在 CI 白名单时镜像该 sha256 固定副本；或独立 sqlite3
  驱动包。
- 路径：非 imported target 消费时用 `dl_iterate_phdr`（dlpi_name，消费者视角）
  或 `dladdr` 替代；完全取不到则跳过 ELF 段断言并注明环境限制。

## 验证

本机 conan create -pr:h=ohos-aarch64 --build=missing 全绿，conan remove 后干净
重跑 RC=0：
- persondatatest 7/7 + personsproxymodeltest 3/3（QSQLITE 自编插件驱动 sqlite
  库真实读写，真实走 QSqlDatabase 路径）
- test_package 12/12（含 KPEOPLE_SO_PATH 路径解析 + ELF 动态段/DT_SONAME/
  DT_RUNPATH 断言）

## 查重结论

- index.tsv 按 `qt_version_tag`、`unixodbc`、`QSQLITE`、`sqldriver`、
  `Cannot mix incompatible Qt` 检索：无命中（Qt 版本线 ABI 互斥+驱动自编组合为空白）。
- HMDFS 路径类已有条目：E011（umask/临时目录权限）、E052（configure 临时目录）、
  E050/E073（符号链接）、E079（硬链接）、E212（安全标签 dlopen）——均为"权限/链接"
  形态；本条"路径查询通道给出不可开路径→configure 期消费者视角注入"是增量新形态。
- Qt CMake 供给形态：E632（FindXxx.cmake 与 CMakeDeps config 遮蔽）讲模块遮蔽，
  本条讲 ABI 线选择+聚合 shim 的三源接线，正交不重叠。

## 红线

- 不得用 cmake 版本约束"绕过"ABI 互斥——混装必在运行期 abort，编译期静默。
- 自编插件必须用与供给 libQt5Sql 同一 tarball 行的源码（qt_version_tag 一致）。
- QT_PLUGIN_PATH 双布局缺一不可（ECMAddTests 的 configure 期冻结会覆盖运行期 env）。
