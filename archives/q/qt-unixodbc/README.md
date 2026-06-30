# qt-unixodbc

## 简介
qt-unixodbc 是 Qt5 的 unixODBC SQL 驱动插件（QODBCDriver），从 qtbase 源码的 `src/plugins/sqldrivers/odbc` 目录单独构建。生成的 `libqsqlodbc.so` 支持 QODBC3 和 QODBC 两种驱动键，通过 unixODBC（libodbc.so）作为中间层连接各种 ODBC 数据源。

## OHOS 适配
- OHOS 环境中安装的 headers 是混合 Qt5(5.12.12)/Qt6(6.11.1)，需手动使用 clang++ 编译
- 需要指定 Qt5 5.12.12 headers 路径（排除 Qt6 headers）
- 需要使用 Qt5 moc 工具生成 `.moc` 文件（Qt6 moc 输出不兼容）
- 需要应用补丁修复 ODBC 源码在 OHOS 环境的兼容性问题
- 链接时需要 `-lohenvironment` 适配 OHOS 平台
- 运行时 dlopen 加载驱动需要 ELF 签名（OHOS 平台限制）

## 依赖
- 编译依赖：qt5-qtbase/5.12.12 (headers + libraries)、unixodbc (libodbc 开发库)
- 运行依赖：Qt5Sql、Qt5Core、libodbc.so.2、ohenvironment、libc++_shared

## 功能验证
```bash
# 检查驱动是否可被Qt加载
ls ~/usr/local/plugins/sqldrivers/libqsqlodbc.so

# 查看驱动依赖
readelf -d libqsqlodbc.so | grep NEEDED

# 查看驱动键（QODBC3, QODBC）
nm -D libqsqlodbc.so | grep QODBC
```

## 参考
- Qt5 SQL驱动文档：https://doc.qt.io/qt-5/sql-driver.html
- Qt5 ODBC驱动源码：qtbase/src/plugins/sqldrivers/odbc/
- unixODBC：http://www.unixodbc.org/