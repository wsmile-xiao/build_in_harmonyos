# qt-mariadb

## 简介
qt-mariadb 是 Qt5 的 MariaDB SQL 驱动插件，从 qtbase 源码的 `src/plugins/sqldrivers/mysql` 目录单独构建。生成的 `libqsqlmysql.so` 支持 QMYSQL3、QMYSQL 和 QMARIADB 三种驱动键，链接 MariaDB 客户端库（libmariadb.so）作为后端。

## OHOS 适配
- OHOS 环境中安装的 headers 是混合 Qt5(5.12.12)/Qt6(6.11.1)，需手动使用 clang++ 编译
- 需要指定 Qt5 5.12.12 headers 路径（排除 Qt6 headers）
- 需要使用 Qt5 moc 工具生成 `.moc` 文件（Qt6 moc 输出不兼容）
- 链接时需要 `-lohenvironment` 适配 OHOS 平台
- 运行时 dlopen 加载驱动需要 ELF 签名（OHOS 平台限制）
- qt-mariadb 与 qt-mysql 使用相同的源码和驱动文件，区别仅在于链接的数据库客户端库

## 排除与替代
- MariaDB 客户端库（libmariadb）替代 MySQL 客户端库（libmysqlclient），兼容性更好
- 不推荐同时安装 qt-mysql 和 qt-mariadb（驱动文件名相同）

## 依赖
- 编译依赖：qt5-qtbase/5.12.12 (headers + libraries)、mariadb (libmariadb 开发库)
- 运行依赖：Qt5Sql、Qt5Core、libmariadb、ohenvironment、libc++_shared

## 功能验证
```bash
# 检查驱动是否可被Qt加载
ls ~/usr/local/plugins/sqldrivers/libqsqlmysql.so

# 查看驱动依赖（应包含libmariadb.so而非libmysqlclient.so）
readelf -d libqsqlmysql.so | grep NEEDED

# 查看驱动键（QMYSQL3, QMYSQL, QMARIADB）
nm -D libqsqlmysql.so | grep QMYSQL
```

## 参考
- Qt5 SQL驱动文档：https://doc.qt.io/qt-5/sql-driver.html
- Qt5 MySQL驱动源码：qtbase/src/plugins/sqldrivers/mysql/
- MariaDB客户端库：https://mariadb.com/kb/en/mariadb-connector-c/