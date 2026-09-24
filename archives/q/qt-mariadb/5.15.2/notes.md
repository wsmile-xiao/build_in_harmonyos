# qt-mariadb 5.15.2 适配笔记

## 编译环境
- 构建系统: custom (conan recipe 内手动 clang++ 编译)
- 编译日期: 2026-08-27 (初版 2026-06-12 探索性编译)
- 编译器: clang/clang++
- 状态: built

## 编译步骤

### 初始化
- 插件源码取自 qtbase 5.15.2 官方源码包 (qtbase-everywhere-src-5.15.2.tar.xz)
  的 src/plugins/sqldrivers/mysql/ 目录（main.cpp / qsql_mysql.cpp / qsql_mysql_p.h / mysql.json），
  通过 exports_sources 直接携带在配方中，避免为 4 个文件下载 50MB 完整 tarball（源文件与上游完全一致，未做修改）
- conandata.yml 中声明上游 URL 与 sha256 以保证可追溯（R39）

### 编译
- 使用 qt5-qtbase/5.15.2 conan 包提供的 Qt5 5.15.2 headers 与 moc 工具
- 使用 Qt5 moc 生成 main.moc
- 手动 clang++ 编译 qsql_mysql.cpp / main.cpp（排除混合环境中的 Qt6 headers）
- 链接 libmariadb 与 Qt5Core；Qt5Sql 符号按 Qt 插件惯例在链接期保持未解析，
  由宿主进程在运行时 dlopen 插件时提供
- 无补丁文件（patches: {}）

### 关键编译参数
```bash
clang++ -c -pipe -O2 -std=c++14 -Wall -Wextra -Wno-deprecated-declarations -D_REENTRANT -fPIC \
  -DQT_NO_CAST_TO_ASCII -DQT_NO_CAST_FROM_ASCII -DQT_NO_DEBUG \
  -DQT_PLUGIN -DQT_SQL_LIB -DQT_CORE_LIB \
  -I[plugin-src] -I[qt5-include/QtCore/5.15.2/QtCore] -I[qt5-include/QtSql/5.15.2/QtSql] \
  -I[qt5-src/sql/kernel] -I[mariadb-include] \
  qsql_mysql.cpp main.cpp

clang++ -shared -o libqsqlmysql.so qsql_mysql.o main.o \
  -L[qt5-lib] -lQt5Core -L[mariadb-lib] -lmariadb \
  -Wl,-soname,libqsqlmysql.so
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 环境中混合 Qt5(5.12.12)/Qt6(6.11.1) headers 导致编译失败 | 安装的 headers 是混合版本，Qt6 headers API 不兼容 Qt5 源码 | 依赖 conan 包 qt5-qtbase/5.15.2，显式指定 5.15.2 版本化 include 路径，排除 Qt6 headers |
| 2 | moc 生成 Qt6 风格输出 | 环境默认 moc 为 Qt6 版本 | 使用 qt5-qtbase/5.15.2 包 bin/ 目录中的 Qt5 moc |
| 3 | 运行时 dlopen 加载失败 | OHOS 平台要求所有动态库必须 ELF 签名 | 平台限制，编译产物本身正确，部署时完成 ELF 签名 |
| 4 | include/QtSql/ 缺少 config 转发头 | qt5-qtbase 构建时 -no-feature-sql，生成头在 src/sql/ 而转发头缺失 | build() 中从 qt5-qtbase 包 src/sql/ 复制 qtsql-config*.h 生成转发头 |

## 依赖版本
- qt5-qtbase/5.15.2 (Qt5 Core/Sql headers + moc)
- mariadb-connector-c/3.4.8 (libmariadb)

## 平台适配说明 (R40)
- qt-mariadb 是 SQL 驱动插件，对 libmariadb 客户端库的薄封装，不涉及窗口/渲染/外设/HAL 交互，
  无需平台适配代码（源文件零修改，patches 为空）
- 平台相关问题（ELF 签名、dlopen 加载）由 Qt 框架层 / 系统层处理

## 验证结果

```bash
# 查看libqsqlmysql.so依赖（qt-mariadb版本链接libmariadb.so而非libmysqlclient.so）
readelf -d libqsqlmysql.so | grep NEEDED
# libQt5Core.so, libmariadb.so, libc++_shared.so, libc.so

# 查看驱动键
# QMYSQL3, QMYSQL, QMARIADB

# 查看导出符号
nm -D libqsqlmysql.so | wc -l
# 60 exported symbols, identical structure to qt-mysql
```

test_package 编译并运行 test_plugin.c，对产物 ELF 做程序化校验：
ELF 共享对象校验、驱动键 QMYSQL/QMARIADB、libmariadb 链接（排除 libmysqlclient）、
Qt 插件接口导出（qt_plugin_instance / qt_plugin_query_metadata）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libqsqlmysql.so | ~138KB | Qt5 MariaDB SQL驱动插件 |

## 注意事项
- qt-mariadb 与 qt-mysql 生成相同的 libqsqlmysql.so，区别仅在于链接的客户端库
- 运行时需要 ELF 签名才能通过 dlopen 加载（OHOS平台限制）
- 编译需指定 Qt5 headers，排除混合环境中的 Qt6 headers
- 不推荐同时安装 qt-mysql 和 qt-mariadb（驱动文件名相同）

**编译结束**: 2026-09-17
**最终状态**: built

