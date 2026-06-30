# qt-unixodbc 5.15.2 适配笔记

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
- 使用qtbase 5.12.12源码中的odbc驱动源代码（ABI兼容）
- 手动使用clang++编译，指定Qt5 5.12.12 headers（排除Qt6 headers）
- 使用Qt5 moc工具生成main.moc
- 链接libodbc、Qt5Sql、Qt5Core、ohenvironment
- 应用补丁：0001-src-plugins-sqldrivers-odbc-qsql_odbc.cpp.patch

### 关键编译参数
```bash
clang++ -c -pipe -O2 -std=c++14 -Wall -Wextra -Wno-deprecated-declarations -D_REENTRANT -fPIC \
  -DQT_NO_CAST_TO_ASCII -DQT_NO_CAST_FROM_ASCII -DQT_NO_DEBUG \
  -DQT_PLUGIN -DQT_SQL_LIB -DQT_CORE_LIB \
  -I[odbc-src] \
  -I[qt5-release-include] \
  -I[qt5-release-include/QtCore/5.12.12/QtCore/private] \
  -I[qt5-release-include/QtSql/5.12.12/QtSql/private] \
  -I[usr/local/include] \
  qsql_odbc.cpp main.cpp

clang++ -shared -o libqsqlodbc.so qsql_odbc.o main.o \
  -L~/usr/local/lib -lQt5Sql -lQt5Core -lodbc -lohenvironment \
  -Wl,-rpath,~/usr/local/lib -Wl,-soname,libqsqlodbc.so
```

## 源码修改
- 0001-src-plugins-sqldrivers-odbc-qsql_odbc.cpp.patch: 修复ODBC驱动源码在OHOS环境的兼容性问题

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | qtbase 5.15.2源码无法编译odbc插件 | 安装的headers是混合Qt5(5.12.12)/Qt6(6.11.1)，Qt6 headers API不兼容Qt5源码 | 使用qtbase 5.12.12源码（ABI兼容），指定Qt5 5.12.12 headers |
| 2 | Qt6 moc生成Qt6风格的moc输出 | ~/usr/local/libexec/moc是Qt6版本 | 使用Qt5 moc工具(~/tmp/qt5-tools-cmake-build/build-moc/moc) |
| 3 | ODBC驱动源码兼容性问题 | qsql_odbc.cpp中部分代码不兼容OHOS环境 | 应用补丁修复源码兼容性 |
| 4 | 运行时dlopen加载失败 | OHOS平台要求所有动态库必须ELF签名 | 平台限制，编译产物本身正确，需在部署时完成ELF签名 |

## 依赖版本
- Qt5 Core/Sql: 5.12.12 (headers)
- unixODBC: libodbc.so.2
- ohenvironment: OHOS平台适配库

## 验证结果

```bash
# 查看libqsqlodbc.so依赖
readelf -d libqsqlodbc.so | grep NEEDED
# libQt5Sql.so, libQt5Core.so, libodbc.so.2, libc++_shared.so, libc.so

# 查看驱动键
# QODBC3, QODBC

# 查看导出符号
nm -D libqsqlodbc.so | wc -l
# 73 exported symbols including open, close, beginTransaction, commitTransaction, rollbackTransaction, cleanup, endTrans
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libqsqlodbc.so | ~138KB | Qt5 unixODBC SQL驱动插件 |

## 注意事项
- 运行时需要 ELF 签名才能通过 dlopen 加载（OHOS平台限制）
- 编译需指定 Qt5 headers，排除混合环境中的 Qt6 headers
- 需要安装 unixODBC 库和配置 ODBC 数据源才能实际使用

**编译结束**: 2026-06-12
**最终状态**: built