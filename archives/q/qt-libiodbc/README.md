# qt-libiodbc

## 简介
qt-libiodbc 是 Qt5 的 iODBC SQL 驱动插件（QIODBCDriver），从 qtbase 源码的 `src/plugins/sqldrivers/odbc` 目录修改构建。生成的 `libqsqliodbc.so` 使用独立的 QIODBC3 和 QIODBC 驱动键，通过 iODBC（libiodbc.so）作为中间层连接各种 ODBC 数据源，与 unixODBC 驱动（QODBC3/QODBC）互不冲突。

## OHOS 适配
- OHOS 环境中安装的 headers 是混合 Qt5(5.12.12)/Qt6(6.11.1)，需手动使用 clang++ 编译
- 需要指定 Qt5 5.12.12 headers 路径（排除 Qt6 headers）
- 需要使用 Qt5 moc 工具生成 `.moc` 文件（Qt6 moc 输出不兼容）
- 链接时需要 `-lohenvironment` 适配 OHOS 平台
- 运行时 dlopen 加载驱动需要 ELF 签名（OHOS 平台限制）
- 驱动需手动部署到 `$PREFIX/sqldrivers/` 目录才能被 Qt 应用正确加载

## 排除与替代
- iODBC 和 unixODBC 可以共存，驱动键不同（QIODBC3/QIODBC vs QODBC3/QODBC）
- iODBC 更适合 macOS/iOS 风格的 ODBC 环境，unixODBC 更适合 Linux 环境

## 依赖
- 编译依赖：qt5-qtbase/5.12.12 (headers + libraries)、libiodbc (libiodbc + libiodbcinst 开发库)
- 运行依赖：Qt5Sql、Qt5Core、libiodbc.so.2、libiodbcinst.so.2、ohenvironment、libc++_shared

## 功能验证
```bash
# 检查驱动是否部署到sqldrivers目录
ls ~/usr/local/plugins/sqldrivers/libqsqliodbc.so

# 查看驱动依赖
readelf -d libqsqliodbc.so | grep NEEDED

# 查看驱动键（QIODBC3, QIODBC — 注意与unixODBC的QODBC区分）
nm -D libqsqliodbc.so | grep QIODBC
```

## 参考
- Qt5 SQL驱动文档：https://doc.qt.io/qt-5/sql-driver.html
- iODBC：http://www.iodbc.org/
- Qt5 ODBC驱动源码：qtbase/src/plugins/sqldrivers/odbc/