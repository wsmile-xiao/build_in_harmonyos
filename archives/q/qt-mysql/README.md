# qt-mysql

## 简介
qt-mysql 是 Qt5 的 MySQL/MariaDB SQL 驱动插件（QMYSQLDriver），从 qtbase 源码的 `src/plugins/sqldrivers/mysql` 目录单独构建。生成的 `libqsqlmysql.so` 同时支持 QMYSQL3、QMYSQL 和 QMARIADB 三种驱动键。

## OHOS 适配
- OHOS 环境中安装的 headers 是混合 Qt5(5.12.12)/Qt6(6.11.1)，无法直接使用 qmake 构建，需手动使用 clang++ 编译
- 需要指定 Qt5 5.12.12 headers 路径（排除 Qt6 headers）
- 需要使用 Qt5 moc 工具生成 `.moc` 文件（Qt6 moc 输出不兼容）
- 链接时需要 `-lohenvironment` 适配 OHOS 平台
- 运行时 dlopen 加载驱动需要 ELF 签名（OHOS 平台限制，非编译问题）

## 排除与替代
- 不推荐使用 Qt6 的 MySQL 驱动（API 不兼容 Qt5）
- MariaDB 客户端库（libmariadb）替代 MySQL 客户端库（libmysqlclient），兼容性更好

## 依赖
- 编译依赖：qt5-qtbase/5.12.12 (headers + libraries)、mariadb (libmariadb 开发库)
- 运行依赖：Qt5Sql、Qt5Core、libmariadb、ohenvironment、libc++_shared

## 功能验证
```bash
# 检查驱动是否可被Qt加载
ls ~/usr/local/plugins/sqldrivers/libqsqlmysql.so

# 查看驱动依赖
readelf -d libqsqlmysql.so | grep NEEDED

# 查看驱动符号
nm -D libqsqlmysql.so | grep QMYSQL
```

## 参考
- Qt5 SQL驱动文档：https://doc.qt.io/qt-5/sql-driver.html
- Qt5 MySQL驱动源码：qtbase/src/plugins/sqldrivers/mysql/