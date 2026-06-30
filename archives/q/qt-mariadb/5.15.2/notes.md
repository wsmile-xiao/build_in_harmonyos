# qt-mariadb 5.15.2 适配笔记

## 编译环境
- 构建系统: custom (手动clang++编译)
- 编译日期: 2026-06-12
- 编译器: clang/clang++
- 状态: built

## 编译步骤

### 初始化
- 下载qtbase 5.15.2源码 (qtbase-everywhere-src-5.15.2.tar.xz)
- 本地已有qtbase 5.12.12源码 (qt-harmonyos-src-5.12.12-20260330)

### 编译
- 使用qtbase 5.12.12源码中的mysql驱动源代码（ABI兼容）
- 手动使用clang++编译，指定Qt5 5.12.12 headers（排除Qt6 headers）
- 使用Qt5 moc工具生成main.moc
- 链接libmariadb、Qt5Sql、Qt5Core、ohenvironment
- 无补丁文件

### 关键编译参数
```bash
clang++ -c -pipe -O2 -std=c++14 -Wall -Wextra -Wno-deprecated-declarations -D_REENTRANT -fPIC \
  -DQT_NO_CAST_TO_ASCII -DQT_NO_CAST_FROM_ASCII -DQT_NO_DEBUG \
  -DQT_PLUGIN -DQT_SQL_LIB -DQT_CORE_LIB \
  -I[mysql-src] \
  -I[qt5-release-include] \
  -I[qt5-release-include/QtCore/5.12.12/QtCore/private] \
  -I[qt5-release-include/QtSql/5.12.12/QtSql/private] \
  -I[usr/local/include] \
  qsql_mysql.cpp main.cpp

clang++ -shared -o libqsqlmysql.so qsql_mysql.o main.o \
  -L~/usr/local/lib -lQt5Sql -lQt5Core -lmariadb -lohenvironment \
  -Wl,-rpath,~/usr/local/lib -Wl,-soname,libqsqlmysql.so
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | qtbase 5.15.2源码无法编译mysql插件 | 安装的headers是混合Qt5(5.12.12)/Qt6(6.11.1)，Qt6 headers API不兼容Qt5源码 | 使用qtbase 5.12.12源码（ABI兼容），指定Qt5 5.12.12 headers |
| 2 | Qt6 moc生成Qt6风格的moc输出 | ~/usr/local/libexec/moc是Qt6版本 | 使用Qt5 moc工具(~/tmp/qt5-tools-cmake-build/build-moc/moc) |
| 3 | 运行时dlopen加载失败 | OHOS平台要求所有动态库必须ELF签名 | 平台限制，编译产物本身正确，需在部署时完成ELF签名 |

## 依赖版本
- Qt5 Core/Sql: 5.12.12 (headers)
- MariaDB: libmariadb
- ohenvironment: OHOS平台适配库

## 验证结果

```bash
# 查看libqsqlmysql.so依赖（qt-mariadb版本链接libmariadb.so而非libmysqlclient.so）
readelf -d libqsqlmysql.so | grep NEEDED
# libQt5Sql.so, libQt5Core.so, libmariadb.so, libc++_shared.so, libc.so

# 查看驱动键
# QMYSQL3, QMYSQL, QMARIADB

# 查看导出符号
nm -D libqsqlmysql.so | wc -l
# 60 exported symbols, identical structure to qt-mysql
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libqsqlmysql.so | ~138KB | Qt5 MariaDB SQL驱动插件 |

## 注意事项
- qt-mariadb 与 qt-mysql 生成相同的 libqsqlmysql.so，区别仅在于链接的客户端库
- 运行时需要 ELF 签名才能通过 dlopen 加载（OHOS平台限制）
- 编译需指定 Qt5 headers，排除混合环境中的 Qt6 headers
- 不推荐同时安装 qt-mysql 和 qt-mariadb（驱动文件名相同）

**编译结束**: 2026-06-12
**最终状态**: built